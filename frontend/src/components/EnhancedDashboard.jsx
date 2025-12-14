import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';
import { Activity, Database, Clock, Search, Brain, TrendingUp, BookOpen, Target, Zap, AlertCircle, CheckCircle, XCircle } from 'lucide-react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

const COLORS = {
  primary: '#667eea',
  secondary: '#764ba2',
  success: '#10b981',
  warning: '#f59e0b',
  error: '#ef4444',
  info: '#3b82f6'
};

const CHART_COLORS = ['#667eea', '#764ba2', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'];

const StatsCard = ({ title, value, icon: Icon, subtext, trend, color = 'primary' }) => (
  <Card className="overflow-hidden hover:shadow-lg transition-shadow duration-300">
    <CardContent className="p-6">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
          {subtext && <p className="text-xs text-gray-500 mt-1">{subtext}</p>}
          {trend && (
            <div className={`flex items-center text-xs mt-2 ${trend > 0 ? 'text-green-600' : 'text-red-600'}`}>
              {trend > 0 ? <TrendingUp className="w-3 h-3 mr-1" /> : <TrendingUp className="w-3 h-3 mr-1 rotate-180" />}
              {Math.abs(trend)}%
            </div>
          )}
        </div>
        <div className={`p-3 rounded-lg bg-gradient-to-br ${color === 'primary' ? 'from-blue-500 to-purple-600' : color === 'success' ? 'from-green-500 to-emerald-600' : 'from-orange-500 to-red-600'}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </CardContent>
  </Card>
);

const StatusBadge = ({ status }) => {
  const statusConfig = {
    'healthy': { color: 'success', icon: CheckCircle, text: 'Healthy' },
    'warning': { color: 'warning', icon: AlertCircle, text: 'Warning' },
    'error': { color: 'error', icon: XCircle, text: 'Error' }
  };

  const config = statusConfig[status] || statusConfig['healthy'];
  const Icon = config.icon;

  return (
    <Badge variant="outline" className={`border-${config.color}-500 text-${config.color}-700 bg-${config.color}-50 dark:bg-${config.color}-900/20`}>
      <Icon className="w-3 h-3 mr-1" />
      {config.text}
    </Badge>
  );
};

const EnhancedDashboard = () => {
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);
  const [themes, setThemes] = useState([]);
  const [consumptionStats, setConsumptionStats] = useState(null);
  const [healthStatus, setHealthStatus] = useState('loading');
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [timeRange, setTimeRange] = useState('7d');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, recentRes, themesRes, consumptionRes, healthRes] = await Promise.all([
          axios.get('/api/stats'),
          axios.get('/api/recent'),
          axios.get('/api/themes'),
          axios.get('/api/consumption/stats'),
          axios.get('/api/health')
        ]);

        setStats(statsRes.data);
        setRecent(recentRes.data.results || []);
        setThemes(themesRes.data.themes || []);
        setConsumptionStats(consumptionRes.data.stats);
        setHealthStatus(healthRes.data.success ? 'healthy' : 'error');
      } catch (error) {
        console.error("Failed to fetch dashboard data", error);
        setHealthStatus('error');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [timeRange]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }

    setIsSearching(true);
    try {
      const response = await axios.post('/api/search/hybrid', {
        query: searchQuery,
        embedding: new Array(384).fill(0.1), // Dummy embedding for demo
        k: 10
      });
      setSearchResults(response.data.results || []);
    } catch (error) {
      console.error("Search failed", error);
    } finally {
      setIsSearching(false);
    }
  };

  const formatChartData = () => {
    if (!themes) return [];
    return themes.slice(0, 6).map(theme => ({
      name: theme.term,
      value: theme.count
    }));
  };

  const formatConsumptionData = () => {
    if (!consumptionStats?.queue_counts) return [];
    const { queue_counts } = consumptionStats;
    return [
      { name: 'Unconsumed', value: queue_counts.unconsumed || 0, color: COLORS.error },
      { name: 'Reading', value: queue_counts.reading || 0, color: COLORS.warning },
      { name: 'Reviewed', value: queue_counts.reviewed || 0, color: COLORS.info },
      { name: 'Applied', value: queue_counts.applied || 0, color: COLORS.success }
    ];
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Welcome back! Here's your knowledge overview.</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={healthStatus} />
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
          </select>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Artifacts"
          value={stats?.total_artifacts || 0}
          icon={Database}
          subtext="In your knowledge base"
          color="primary"
          trend={5}
        />
        <StatsCard
          title="Consumption Rate"
          value={`${stats?.consumption_rate || 0}%`}
          icon={Activity}
          subtext="Average consumption"
          color="success"
          trend={12}
        />
        <StatsCard
          title="Queue Size"
          value={consumptionStats?.queue_counts?.unconsumed || 0}
          icon={Clock}
          subtext="Pending consumption"
          color="warning"
          trend={-3}
        />
        <StatsCard
          title="Knowledge Score"
          value={stats?.knowledge_score || 0}
          icon={Brain}
          subtext="Overall score"
          color="primary"
          trend={8}
        />
      </div>

      {/* Search Bar */}
      <Card>
        <CardContent className="p-6">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <Input
                placeholder="Search your knowledge base..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                className="pl-10 pr-4"
              />
            </div>
            <Button onClick={handleSearch} disabled={isSearching}>
              {isSearching ? 'Searching...' : 'Search'}
            </Button>
          </div>

          {searchResults && (
            <div className="mt-4 max-h-60 overflow-y-auto">
              <h4 className="font-semibold mb-2">Search Results</h4>
              {searchResults.length > 0 ? (
                <div className="space-y-2">
                  {searchResults.map((result, index) => (
                    <div key={index} className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                      <h5 className="font-medium">{result.artifact?.title || 'Untitled'}</h5>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Score: {(result.combined_score * 100).toFixed(1)}%
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 dark:text-gray-400">No results found</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Themes Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-5 h-5" />
              Top Themes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={formatChartData()}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill={COLORS.primary} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Consumption Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="w-5 h-5" />
              Consumption Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={formatConsumptionData()}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {formatConsumptionData().map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Recent Artifacts */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Clock className="w-5 h-5" />
              Recent Artifacts
            </span>
            <Button variant="outline" size="sm">
              View All
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {recent.slice(0, 5).map((artifact, index) => (
              <div key={index} className="flex items-center justify-between p-3 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg transition-colors">
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-gray-900 dark:text-white truncate">
                    {artifact.title}
                  </h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {new Date(artifact.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={artifact.consumption_status === 'unconsumed' ? 'destructive' : 'secondary'}>
                    {artifact.consumption_status}
                  </Badge>
                  <Badge variant="outline">
                    {(artifact.importance_score || 0).toFixed(1)}
                  </Badge>
                </div>
              </div>
            ))}
            {recent.length === 0 && (
              <p className="text-center text-gray-500 dark:text-gray-400 py-8">
                No recent artifacts
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <CardContent className="p-4 text-center">
            <Zap className="w-8 h-8 mx-auto mb-2 text-primary-600" />
            <p className="font-medium">Quick Capture</p>
          </CardContent>
        </Card>
        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <CardContent className="p-4 text-center">
            <Brain className="w-8 h-8 mx-auto mb-2 text-purple-600" />
            <p className="font-medium">Generate Insights</p>
          </CardContent>
        </Card>
        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <CardContent className="p-4 text-center">
            <Target className="w-8 h-8 mx-auto mb-2 text-green-600" />
            <p className="font-medium">Review Queue</p>
          </CardContent>
        </Card>
        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <CardContent className="p-4 text-center">
            <Activity className="w-8 h-8 mx-auto mb-2 text-orange-600" />
            <p className="font-medium">View Graph</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default EnhancedDashboard;