/**
 * Health Check API Endpoint
 * Used by Pxxl.app for deployment health checks
 */

import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Basic health check
    const healthData = {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
      services: {
        frontend: 'operational',
        supabase: process.env.NEXT_PUBLIC_SUPABASE_URL ? 'configured' : 'not_configured',
        huggingface: process.env.NEXT_PUBLIC_HF_API_TOKEN ? 'configured' : 'not_configured',
      },
      environment: {
        node_env: process.env.NODE_ENV,
        next_public_app_name: process.env.NEXT_PUBLIC_APP_NAME,
      }
    };

    return res.status(200).json(healthData);
  } catch (error) {
    console.error('Health check error:', error);
    return res.status(500).json({
      status: 'unhealthy',
      error: 'Health check failed',
      timestamp: new Date().toISOString(),
    });
  }
}
