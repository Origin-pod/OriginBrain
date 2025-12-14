import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  BookOpen,
  Clock,
  CheckCircle,
  AlertCircle,
  TrendingUp,
  Target,
  BarChart3,
  Brain,
  Database
} from 'lucide-react';
import axios from 'axios';

const ConsumptionDashboard = () => {
  const [analytics, setAnalytics] = useState(null);
  const [consumptionQueue, setConsumptionQueue] = useState([]);
  const [trends, setTrends] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [analyticsRes, queueRes, trendsRes] = await Promise.all([
          axios.get('/api/analytics/dashboard'),
          axios.get('/api/consumption/queue?type=daily&limit=10'),
          axios.get('/api/insights/trends?days=7')
        ]);

        setAnalytics(analyticsRes.data.analytics);
        setConsumptionQueue(queueRes.data.queue || []);
        setTrends(trendsRes.data.trends || []);
      } catch (error) {
        console.error("Failed to fetch consumption dashboard data", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // Refresh queue every 30 seconds
    const interval = setInterval(() => {
      axios.get('/api/consumption/queue?type=daily&limit=10')
        .then(res => setConsumptionQueue(res.data.queue || []))
        .catch(console.error);
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const handleTrackEvent = async (artifactId, eventType) => {
    try {
      await axios.post('/api/consumption/track', {
        artifact_id: artifactId,
        event_type: eventType,
        source: 'consumption_dashboard'
      });

      // Update local state
      setConsumptionQueue(prev =>
        prev.map(item =>
          item.id === artifactId
            ? { ...item, tracked: true }
            : item
        )
      );
    } catch (error) {
      console.error("Failed to track event:", error);
    }
  };

  const getConsumptionColor = (status) => {
    switch (status) {
      case 'unconsumed': return 'bg-red-100 text-red-800 border-red-200';
      case 'reading': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'reviewed': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'applied': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getPriorityColor = (importance) => {
    if (importance >= 0.8) return 'text-red-600';
    if (importance >= 0.6) return 'text-orange-600';
    if (importance >= 0.4) return 'text-yellow-600';
    return 'text-gray-600';
  };

  const getPriorityBadge = (importance) => {
    if (importance >= 0.8) return { color: 'bg-red-500', label: 'Critical' };
    if (importance >= 0.6) return { color: 'bg-orange-500', label: 'High' };
    if (importance >= 0.4) return { color: 'bg-yellow-500', label: 'Medium' };
    return { color: 'bg-gray-500', label: 'Low' };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-blue-600">Total Artifacts</p>
                <p className="text-2xl font-bold text-blue-900">{analytics?.total_artifacts || 0}</p>
              </div>
              <Database className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-green-600">Applied Knowledge</p>
                <p className="text-2xl font-bold text-green-900">
                  {analytics?.consumption_stats?.applied || 0}
                </p>
                <p className="text-xs text-green-600 mt-1">
                  {((analytics?.consumption_rate || 0) * 100).toFixed(1)}% rate
                </p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-yellow-50 to-yellow-100 border-yellow-200">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-yellow-600">In Progress</p>
                <p className="text-2xl font-bold text-yellow-900">
                  {analytics?.consumption_stats?.reading || 0}
                </p>
              </div>
              <Clock className="h-8 w-8 text-yellow-500" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-red-50 to-red-100 border-red-200">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-red-600">Unconsumed</p>
                <p className="text-2xl font-bold text-red-900">
                  {analytics?.consumption_stats?.unconsumed || 0}
                </p>
              </div>
              <AlertCircle className="h-8 w-8 text-red-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Consumption Queue */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              Today's Consumption Queue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {consumptionQueue.length === 0 ? (
                <p className="text-center text-gray-500 py-8">No items in your consumption queue</p>
              ) : (
                consumptionQueue.map((item) => {
                  const priority = getPriorityBadge(item.importance_score || 0.5);
                  return (
                    <div
                      key={item.id}
                      className={`border rounded-lg p-4 transition-all hover:shadow-md ${
                        getConsumptionColor(item.consumption_status)
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          <h4 className="font-semibold text-sm">{item.title}</h4>
                          <p className="text-xs opacity-75 mt-1 line-clamp-2">
                            {item.reason || 'Recommended for consumption'}
                          </p>
                        </div>
                        <div className="flex flex-col items-end gap-2">
                          <Badge className={`${priority.color} text-white text-xs`}>
                            {priority.label}
                          </Badge>
                          {item.estimated_read_time && (
                            <span className="text-xs opacity-75">
                              {item.estimated_read_time}m
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center justify-between">
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleTrackEvent(item.id, 'view')}
                            className="text-xs"
                          >
                            View
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleTrackEvent(item.id, 'read')}
                            className="text-xs bg-blue-600 hover:bg-blue-700"
                          >
                            Mark as Read
                          </Button>
                        </div>
                        <div className="flex items-center gap-1">
                          <TrendingUp className="h-3 w-3" />
                          <span className="text-xs font-medium">
                            {(item.score || 0).toFixed(2)}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </CardContent>
        </Card>

        {/* Trending Topics */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Trending Topics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {trends.length === 0 ? (
                <p className="text-center text-gray-500 py-4">No trends yet</p>
              ) : (
                trends.map((trend, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="text-sm font-medium">{trend.topic}</p>
                      <p className="text-xs text-gray-500">
                        {trend.frequency} occurrences
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                        <span className="text-xs font-bold text-blue-600">
                          {index + 1}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Consumption Progress */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            Consumption Progress
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {Object.entries(analytics?.consumption_stats || {}).map(([status, count]) => {
              const total = analytics?.total_artifacts || 1;
              const percentage = (count / total) * 100;
              return (
                <div key={status} className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="capitalize">{status.replace('_', ' ')}</span>
                    <span className="font-medium">{count}</span>
                  </div>
                  <Progress value={percentage} className="h-2" />
                  <p className="text-xs text-gray-500">{percentage.toFixed(1)}%</p>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ConsumptionDashboard;