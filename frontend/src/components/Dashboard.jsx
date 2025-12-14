import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, Database, Clock, Search } from 'lucide-react';
import axios from 'axios';

const StatsCard = ({ title, value, icon: Icon, subtext }) => (
  <div className="bg-white/10 backdrop-blur-md border border-white/20 p-6 rounded-2xl shadow-xl">
    <div className="flex items-center justify-between mb-4">
      <h3 className="text-gray-400 text-sm font-medium">{title}</h3>
      <Icon className="text-blue-400 w-5 h-5" />
    </div>
    <div className="text-3xl font-bold text-white mb-1">{value}</div>
    {subtext && <div className="text-xs text-gray-400">{subtext}</div>}
  </div>
);

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);
  const [themes, setThemes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, recentRes, themesRes] = await Promise.all([
          axios.get('/api/stats'),
          axios.get('/api/recent'),
          axios.get('/api/themes')
        ]);
        setStats(statsRes.data);
        setRecent(recentRes.data.results);
        setThemes(themesRes.data.themes);
      } catch (error) {
        console.error("Failed to fetch dashboard data", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Load Twitter Widgets Script
  useEffect(() => {
    if (window.twttr) {
      window.twttr.widgets.load();
    } else {
      if (!document.getElementById('twitter-wjs')) {
        const script = document.createElement('script');
        script.id = 'twitter-wjs';
        script.src = "https://platform.twitter.com/widgets.js";
        script.async = true;
        document.body.appendChild(script);
      }
    }
  }, []); // Run only once

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    
    setIsSearching(true);
    try {
      const res = await axios.post('/search', { query: searchQuery });
      setSearchResults(res.data.results);
    } catch (error) {
      console.error("Search failed", error);
    } finally {
      setIsSearching(false);
    }
  };

  if (loading) return <div className="text-white p-10">Loading Pulse...</div>;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header & Search */}
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-500">
            Brain Pulse
          </h1>
          <p className="text-gray-400 mt-2">Your knowledge base at a glance.</p>
        </div>
        
        <div className="flex-1 max-w-xl mx-8">
          <form onSubmit={handleSearch} className="relative">
            <Search className="absolute left-4 top-3.5 text-gray-400 w-5 h-5" />
            <input 
              type="text" 
              placeholder="Search your second brain..." 
              className="w-full bg-white/5 border border-white/10 rounded-full py-3 pl-12 pr-4 text-white focus:outline-none focus:border-blue-500 transition"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </form>
        </div>

        <div className="text-right">
          <div className="text-sm text-gray-500">Last Synced</div>
          <div className="text-white font-mono">
            {new Date(stats?.last_updated * 1000).toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* Search Results Overlay */}
      {searchResults && (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-8 animate-in fade-in slide-in-from-top-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-white">
              Results for "{searchQuery}"
            </h2>
            <button 
              onClick={() => { setSearchResults(null); setSearchQuery(''); }}
              className="text-gray-400 hover:text-white"
            >
              Clear
            </button>
          </div>
          
          <div className="space-y-4">
            {searchResults.length > 0 ? (
              searchResults.map((result, idx) => (
                <div key={idx} className={`p-4 rounded-xl border ${idx === 0 ? 'bg-blue-500/10 border-blue-500/30' : 'bg-white/5 border-white/10'}`}>
                  {idx === 0 && (
                    <div className="text-xs font-bold text-blue-400 mb-2 uppercase tracking-wider">
                      Best Match
                    </div>
                  )}
                  <div className="flex justify-between items-start">
                    <h3 className="text-white font-medium truncate pr-4">
                      {result.source.startsWith('http') ? (
                        <a href={result.source} target="_blank" rel="noreferrer" className="hover:underline">
                          {result.source}
                        </a>
                      ) : result.source}
                    </h3>
                    <span className="text-xs text-gray-500">
                      {new Date(result.date).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="text-gray-300 text-sm mt-2 leading-relaxed">
                     {result.content.includes('<blockquote class="twitter-tweet"') ? (
                        <div dangerouslySetInnerHTML={{ __html: result.content }} />
                      ) : (
                        <p>{result.content.substring(0, 300)}...</p>
                      )}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-gray-400 text-center py-8">No results found.</div>
            )}
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatsCard 
          title="Total Artifacts" 
          value={stats?.total_count} 
          icon={Database} 
          subtext="Across all sources"
        />
        <StatsCard 
          title="Daily Activity" 
          value={stats?.daily_activity?.reduce((acc, curr) => acc + curr.count, 0)} 
          icon={Activity} 
          subtext="Last 30 days"
        />
        <StatsCard 
          title="Recent Drops" 
          value={recent.length} 
          icon={Clock} 
          subtext="Latest captures"
        />
      </div>

      {/* Activity Graph */}
      <div className="bg-white/5 border border-white/10 p-6 rounded-2xl">
        <h2 className="text-xl font-semibold text-white mb-6">Activity Trend</h2>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={stats?.daily_activity}>
              <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }}
                itemStyle={{ color: '#fff' }}
              />
              <Bar dataKey="count" fill="#818cf8" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Items & Themes */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Items */}
        <div>
          <h2 className="text-xl font-semibold text-white mb-4">Recent Captures</h2>
          <div className="h-[600px] overflow-y-auto space-y-4 pr-2">
            {recent.map((item) => (
              <div key={item.id} className="bg-white/5 hover:bg-white/10 transition p-4 rounded-xl border border-white/10 group cursor-pointer">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-blue-300 font-medium truncate pr-4">{item.title || "Untitled"}</h3>
                  <span className="text-xs text-gray-500 whitespace-nowrap">
                    {new Date(item.created_at).toLocaleDateString()}
                  </span>
                </div>
                
                {/* Content Rendering */}
                <div className="text-gray-400 text-sm mt-2">
                  {item.content.includes('<blockquote class="twitter-tweet"') ? (
                    <div dangerouslySetInnerHTML={{ __html: item.content }} />
                  ) : (
                    <p className="line-clamp-3">{item.content.substring(0, 300)}...</p>
                  )}
                </div>

                <div className="mt-3 flex gap-2 flex-wrap">
                  {item.metadata?.tags?.map(tag => (
                    <span key={tag} className="text-xs px-2 py-1 rounded-full bg-blue-500/20 text-blue-300">
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Themes Section */}
        <div>
          <h2 className="text-xl font-semibold text-white mb-4">Top Themes</h2>
          <div className="space-y-4">
            {themes.length > 0 ? (
              themes.map((theme) => (
                <div key={theme.id} className="bg-white/5 p-4 rounded-xl border border-white/10">
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="text-purple-300 font-medium">{theme.name}</h3>
                    <span className="bg-purple-500/20 text-purple-300 text-xs px-2 py-1 rounded-full">
                      {theme.count} items
                    </span>
                  </div>
                  <div className="text-xs text-gray-400">
                    Includes: {theme.sample_titles.join(', ')}
                  </div>
                </div>
              ))
            ) : (
              <div className="bg-gradient-to-br from-purple-900/20 to-blue-900/20 border border-white/10 rounded-2xl p-8 text-center">
                <p className="text-gray-400">Not enough data to cluster themes yet.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
