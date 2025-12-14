import React, { useState } from 'react';
import EnhancedNavigation from './components/EnhancedNavigation';
import EnhancedDashboard from './components/EnhancedDashboard';
import ConsumptionDashboard from './components/ConsumptionDashboard';
import KnowledgeGraph from './components/KnowledgeGraph';
import GoalManager from './components/GoalManager';

function App() {
  const [activeView, setActiveView] = useState('dashboard');

  const renderView = () => {
    switch (activeView) {
      case 'dashboard':
        return <EnhancedDashboard />;
      case 'consumption':
        return <ConsumptionDashboard />;
      case 'knowledge-graph':
        return <KnowledgeGraph />;
      case 'goals':
        return <GoalManager />;
      default:
        return <EnhancedDashboard />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 text-gray-900 dark:text-slate-200 font-sans selection:bg-blue-500/30">
      <EnhancedNavigation activeView={activeView} onViewChange={setActiveView} />
      <main className="container mx-auto px-6 py-8">
        {renderView()}
      </main>
    </div>
  );
}

export default App;
