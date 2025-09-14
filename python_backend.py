#!/usr/bin/env python3
"""
Python Backend API for Tauri Patcher App
Provides REST API endpoints for the patcher functionality
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add the current directory to the path to import our modules
sys.path.insert(0, str(Path(__file__).parent))

from aiohttp import web, ClientSession
from aiohttp.web import Response
import aiofiles
import yaml

# Import our existing modules
from downloader.updater import update_files
from logger import log_info, log_error, log_debug
from settings import load_config

class PatcherAPI:
    def __init__(self):
        self.app = web.Application()
        self.setup_routes()
        self.setup_cors()

    def setup_cors(self):
        """Setup CORS for frontend communication"""
        async def cors_middleware(request, handler):
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response

        async def cors_options_handler(request):
            response = Response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response

        self.app.middlewares.append(cors_middleware)
        self.app.router.add_options('/{path:.*}', cors_options_handler)

    def setup_routes(self):
        """Setup API routes"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/config', self.get_config)
        self.app.router.add_post('/config', self.save_config)
        self.app.router.add_post('/update', self.start_update)
        self.app.router.add_get('/status', self.get_status)

    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({'status': 'healthy', 'service': 'patcher-backend'})

    async def get_config(self, request):
        """Get current configuration"""
        try:
            if os.path.exists('config.yaml'):
                with open('config.yaml', 'r') as f:
                    config = yaml.safe_load(f)

                # Convert to frontend format
                frontend_config = {
                    'serverUrl': config.get('SERVER_URL', ''),
                    'targetFolder': config.get('TARGET_FOLDER', 'patcher'),
                    'fileListUrl': config.get('FILELIST_URL', ''),
                    'downloadSpeedLimit': config.get('DOWNLOAD_SPEED_LIMIT', 0)
                }
                return web.json_response(frontend_config)
            else:
                # Return default config
                return web.json_response({
                    'serverUrl': '',
                    'targetFolder': 'patcher',
                    'fileListUrl': '',
                    'downloadSpeedLimit': 0
                })
        except Exception as e:
            log_error(f"Error loading config: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def save_config(self, request):
        """Save configuration"""
        try:
            data = await request.json()

            # Convert from frontend format to backend format
            config = {
                'SERVER_URL': data.get('serverUrl', ''),
                'TARGET_FOLDER': data.get('targetFolder', 'patcher'),
                'FILELIST_URL': data.get('fileListUrl', ''),
                'DOWNLOAD_SPEED_LIMIT': data.get('downloadSpeedLimit', 0),
                'MULTITHREADING_THRESHOLD': 10485760,  # 10MB
                'PROGRESS_FILE_MAX_AGE': 86400  # 24 hours
            }

            with open('config.yaml', 'w') as f:
                yaml.dump(config, f)

            log_info("Configuration saved successfully")
            return web.json_response({'success': True})

        except Exception as e:
            log_error(f"Error saving config: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def start_update(self, request):
        """Start the update process"""
        try:
            data = await request.json()
            config_data = data.get('config', {})

            # Save config first
            await self.save_config_internal(config_data)

            # Create progress callback that stores progress in memory
            progress_data = {'progress': 0, 'total': 0, 'logs': [], 'completed': False, 'error': None}

            def progress_callback(progress, total, error=None):
                progress_data['progress'] = progress
                progress_data['total'] = total
                if error:
                    progress_data['error'] = error
                    progress_data['logs'].append({'message': f"Error: {error}", 'type': 'error'})
                elif progress is not None and total is not None:
                    percentage = int(progress / total * 100) if total > 0 else 0
                    if progress == total:
                        progress_data['completed'] = True
                        progress_data['logs'].append({'message': f"Update completed!", 'type': 'success'})
                    elif percentage % 10 == 0:  # Log every 10%
                        progress_data['logs'].append({'message': f"Progress: {percentage}%", 'type': 'info'})

            # Store progress data for status endpoint
            self.current_progress = progress_data

            # Start update in background
            asyncio.create_task(self.run_update_process(progress_callback))

            return web.json_response({'success': True, 'message': 'Update process started'})

        except Exception as e:
            log_error(f"Error starting update: {e}")
            return web.json_response({'error': str(e)}, status=500)

    async def save_config_internal(self, config_data):
        """Internal method to save config"""
        config = {
            'SERVER_URL': config_data.get('serverUrl', ''),
            'TARGET_FOLDER': config_data.get('targetFolder', 'patcher'),
            'FILELIST_URL': config_data.get('fileListUrl', ''),
            'DOWNLOAD_SPEED_LIMIT': config_data.get('downloadSpeedLimit', 0),
            'MULTITHREADING_THRESHOLD': 10485760,  # 10MB
            'PROGRESS_FILE_MAX_AGE': 86400  # 24 hours
        }

        with open('config.yaml', 'w') as f:
            yaml.dump(config, f)

    async def run_update_process(self, callback):
        """Run the actual update process"""
        try:
            # Reload settings to get the new config
            import importlib
            import settings
            importlib.reload(settings)

            status_report = await update_files(callback=callback)

            # Update progress data with final results
            if hasattr(self, 'current_progress'):
                self.current_progress['status_report'] = {
                    'updated': status_report['updated'],
                    'skipped': status_report['skipped'],
                    'failed': status_report['failed'],
                    'verification': status_report['verification']
                }
                self.current_progress['completed'] = True

                if status_report['failed']:
                    self.current_progress['logs'].append({
                        'message': f"Warning: {len(status_report['failed'])} files failed to update",
                        'type': 'error'
                    })

                self.current_progress['logs'].append({
                    'message': f"Final result: {len(status_report['updated'])} updated, {len(status_report['skipped'])} skipped",
                    'type': 'success'
                })

        except Exception as e:
            log_error(f"Error in update process: {e}")
            if hasattr(self, 'current_progress'):
                self.current_progress['error'] = str(e)
                self.current_progress['completed'] = True
                self.current_progress['logs'].append({
                    'message': f"Error during update: {str(e)}",
                    'type': 'error'
                })

    async def get_status(self, request):
        """Get current update status"""
        if hasattr(self, 'current_progress'):
            return web.json_response(self.current_progress)
        else:
            return web.json_response({
                'progress': 0,
                'total': 0,
                'logs': [],
                'completed': False,
                'error': None
            })

async def main():
    """Main function to start the API server"""
    log_info("Starting Patcher Backend API...")

    # Create logs directory
    os.makedirs('logs', exist_ok=True)

    # Create API instance
    api = PatcherAPI()

    # Start the server
    runner = web.AppRunner(api.app)
    await runner.setup()

    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()

    log_info("Backend API started on http://localhost:8080")
    print("Backend API started on http://localhost:8080")
    print("Health check: http://localhost:8080/health")

    # Keep the server running
    try:
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour
    except KeyboardInterrupt:
        log_info("Shutting down backend API...")
        await runner.cleanup()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBackend API stopped")
    except Exception as e:
        log_error(f"Fatal error: {e}")
        print(f"Fatal error: {e}")
        sys.exit(1)