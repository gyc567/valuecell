"""
Vercel Serverless Function for ValueCell API.
Simplified API endpoint that handles basic requests.
"""

import json
from typing import Dict, Any


def handler(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main handler for Vercel Serverless Function.

    Args:
        request: Request object containing method, path, headers, body, etc.

    Returns:
        Dict containing statusCode, headers, and body
    """
    method = request.get('method', 'GET')
    path = request.get('path', '/')
    headers = request.get('headers', {})

    # CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, PUT, DELETE',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    }

    # Handle CORS preflight
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': ''
        }

    # Route handling
    if path == '/' or path == '/api/v1':
        return {
            'statusCode': 200,
            'headers': {**cors_headers, 'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'data': {
                    'name': 'ValueCell',
                    'version': '0.1.0',
                    'environment': 'vercel'
                },
                'message': 'Welcome to ValueCell API'
            })
        }

    if path == '/api/v1/health':
        return {
            'statusCode': 200,
            'headers': {**cors_headers, 'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'data': {'status': 'healthy'},
                'message': 'Service is running'
            })
        }

    # Default 404
    return {
        'statusCode': 404,
        'headers': {**cors_headers, 'Content-Type': 'application/json'},
        'body': json.dumps({
            'success': False,
            'error': 'Not Found',
            'message': f'Endpoint {path} not found'
        })
    }
