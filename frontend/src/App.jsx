import React, { useState } from 'react';
import Navigation from './components/Navigation';
import Dashboard from './components/Dashboard';
import ConsumptionDashboard from './components/ConsumptionDashboard';
import KnowledgeGraph from './components/KnowledgeGraph';
import GoalManager from './components/GoalManager';

function App() {
  const [activeView, setActiveView] = useState('dashboard');

  const renderView = () => {
    switch (activeView) {
      case 'dashboard':
        return <Dashboard />;
      case 'consumption':
        return <ConsumptionDashboard />;
      case 'knowledge-graph':
        return <KnowledgeGraph />;
      case 'goals':
        return <GoalManager />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="min-h-screen bg-[#0f172a] text-slate-200 font-sans selection:bg-blue-500/30">
      <Navigation activeView={activeView} onViewChange={setActiveView} />
      <main className="container mx-auto px-6 py-8">
        {renderView()}
      </main>
    </div>
  );
}

export default App;
