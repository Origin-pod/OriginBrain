import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import {
  Plus,
  Target,
  CheckCircle,
  Clock,
  TrendingUp,
  Trash2,
  Edit,
  BookOpen
} from 'lucide-react';
import axios from 'axios';

const GoalManager = () => {
  const [goals, setGoals] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [editingGoal, setEditingGoal] = useState(null);
  const [formData, setFormData] = useState({
    goal: '',
    description: '',
    priority: 5,
    tags: '',
    related_topics: ''
  });

  useEffect(() => {
    fetchGoals();
    fetchRecommendations();
  }, []);

  const fetchGoals = async () => {
    try {
      const response = await axios.get('/api/goals');
      setGoals(response.data.goals || []);
    } catch (error) {
      console.error('Failed to fetch goals:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRecommendations = async () => {
    try {
      if (goals.length > 0) {
        const recPromises = goals.map(goal =>
          axios.post('/api/recommendations/goal-focused', {
            goal_id: goal.id,
            limit: 3
          })
        );
        const responses = await Promise.all(recPromises);
        setRecommendations(responses.map(res => res.data.recommendations || []).flat());
      }
    } catch (error) {
      console.error('Failed to fetch recommendations:', error);
    }
  };

  const handleCreateGoal = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/api/goals', {
        goal: formData.goal,
        description: formData.description,
        priority: formData.priority,
        tags: formData.tags.split(',').map(t => t.trim()).filter(t => t),
        related_topics: formData.related_topics.split(',').map(t => t.trim()).filter(t => t)
      });

      // Reset form
      setFormData({
        goal: '',
        description: '',
        priority: 5,
        tags: '',
        related_topics: ''
      });
      setIsCreateDialogOpen(false);

      // Refresh goals
      fetchGoals();
    } catch (error) {
      console.error('Failed to create goal:', error);
    }
  };

  const handleUpdateGoal = async (e) => {
    e.preventDefault();
    // Update functionality would need additional API endpoint
    console.log('Update goal:', editingGoal.id, formData);
    // Implementation would go here
  };

  const getPriorityColor = (priority) => {
    if (priority >= 8) return 'bg-red-100 text-red-800 border-red-200';
    if (priority >= 6) return 'bg-orange-100 text-orange-800 border-orange-200';
    if (priority >= 4) return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    return 'bg-green-100 text-green-800 border-green-200';
  };

  const getPriorityLabel = (priority) => {
    if (priority >= 8) return 'Critical';
    if (priority >= 6) return 'High';
    if (priority >= 4) return 'Medium';
    return 'Low';
  };

  const formatDate = (dateString) => {
    if (!dateString) return null;
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Goals & Learning Objectives</h2>
          <p className="text-gray-600 mt-1">
            Track your learning goals and get personalized recommendations
          </p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              New Goal
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Goal</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateGoal} className="space-y-4">
              <div>
                <Label htmlFor="goal">Goal *</Label>
                <Input
                  id="goal"
                  placeholder="e.g., Master React hooks"
                  value={formData.goal}
                  onChange={(e) => setFormData({ ...formData, goal: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Describe what you want to achieve..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="priority">Priority (1-10)</Label>
                <Input
                  id="priority"
                  type="number"
                  min="1"
                  max="10"
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
                />
              </div>
              <div>
                <Label htmlFor="tags">Tags (comma-separated)</Label>
                <Input
                  id="tags"
                  placeholder="frontend, react, javascript"
                  value={formData.tags}
                  onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="topics">Related Topics (comma-separated)</Label>
                <Input
                  id="topics"
                  placeholder="hooks, state management, components"
                  value={formData.related_topics}
                  onChange={(e) => setFormData({ ...formData, related_topics: e.target.value })}
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsCreateDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit">Create Goal</Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Goals List */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="text-lg font-semibold">Active Goals</h3>
          {goals.length === 0 ? (
            <Card>
              <CardContent className="p-8 text-center">
                <Target className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">No active goals yet</p>
                <p className="text-sm text-gray-400 mt-2">
                  Create your first goal to start tracking your learning journey
                </p>
              </CardContent>
            </Card>
          ) : (
            goals.map((goal) => (
              <Card key={goal.id} className="relative">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <h4 className="font-semibold text-lg">{goal.goal}</h4>
                      {goal.description && (
                        <p className="text-sm text-gray-600 mt-1">{goal.description}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={getPriorityColor(goal.priority)}>
                        {getPriorityLabel(goal.priority)}
                      </Badge>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setEditingGoal(goal)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>Progress</span>
                        <span>{Math.round((goal.progress || 0) * 100)}%</span>
                      </div>
                      <Progress value={(goal.progress || 0) * 100} className="h-2" />
                    </div>

                    {goal.tags && goal.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {goal.tags.map((tag, index) => (
                          <Badge key={index} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}

                    {goal.related_topics && goal.related_topics.length > 0 && (
                      <div className="text-xs text-gray-500">
                        Topics: {goal.related_topics.join(', ')}
                      </div>
                    )}

                    <div className="flex justify-between text-xs text-gray-500">
                      <span>Created: {formatDate(goal.created_at)}</span>
                      {goal.completed_at && (
                        <span className="text-green-600">
                          <CheckCircle className="h-3 w-3 inline mr-1" />
                          Completed: {formatDate(goal.completed_at)}
                        </span>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>

        {/* Recommendations */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Recommended for Your Goals</h3>
          {recommendations.length === 0 ? (
            <Card>
              <CardContent className="p-6 text-center">
                <BookOpen className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">No recommendations yet</p>
                <p className="text-sm text-gray-400 mt-2">
                  Create goals to get personalized content recommendations
                </p>
              </CardContent>
            </Card>
          ) : (
            recommendations.map((rec) => (
              <Card key={rec.id} className="p-4">
                <div className="space-y-2">
                  <h5 className="font-medium text-sm line-clamp-2">{rec.title}</h5>
                  {rec.reasons && rec.reasons.length > 0 && (
                    <div className="text-xs text-gray-600">
                      {rec.reasons[0]}
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <div className="text-xs text-gray-500">
                      {rec.estimated_read_time}m read
                    </div>
                    <Button size="sm" variant="outline" className="text-xs">
                      View
                    </Button>
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      </div>

      {/* Stats Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Learning Progress Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{goals.length}</div>
              <div className="text-sm text-gray-600">Active Goals</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {goals.filter(g => g.progress >= 1).length}
              </div>
              <div className="text-sm text-gray-600">Completed</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-600">
                {Math.round(goals.reduce((acc, g) => acc + (g.progress || 0), 0) / Math.max(goals.length, 1) * 100)}%
              </div>
              <div className="text-sm text-gray-600">Average Progress</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">{recommendations.length}</div>
              <div className="text-sm text-gray-600">Recommendations</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default GoalManager;