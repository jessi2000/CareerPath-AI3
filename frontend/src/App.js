import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [currentStep, setCurrentStep] = useState('welcome'); // welcome, assessment, roadmap, dashboard
  const [user, setUser] = useState(null);
  const [assessmentData, setAssessmentData] = useState({
    education_level: '',
    work_experience: '',
    current_role: '',
    target_role: '',
    industry: '',
    skills: [],
    timeline_months: 6,
    availability_hours_per_week: 10
  });
  const [roadmap, setRoadmap] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchLeaderboard();
  }, []);

  const fetchLeaderboard = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/leaderboard`);
      const data = await response.json();
      setLeaderboard(data);
    } catch (error) {
      console.error('Error fetching leaderboard:', error);
    }
  };

  const handleAssessmentSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      // Generate roadmap using AI
      const response = await fetch(`${API_BASE}/api/generate-roadmap?user_name=User`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(assessmentData),
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate roadmap');
      }
      
      const generatedRoadmap = await response.json();
      setRoadmap(generatedRoadmap);
      setCurrentStep('roadmap');
    } catch (error) {
      console.error('Error generating roadmap:', error);
      alert('Failed to generate roadmap. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const updateMilestoneStatus = async (milestoneId, status) => {
    if (!roadmap) return;
    
    try {
      const response = await fetch(`${API_BASE}/api/roadmaps/${roadmap.id}/progress`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          milestone_id: milestoneId,
          status: status
        }),
      });
      
      if (response.ok) {
        // Update local roadmap state
        const updatedMilestones = roadmap.milestones.map(m => 
          m.id === milestoneId ? { ...m, status } : m
        );
        setRoadmap({ ...roadmap, milestones: updatedMilestones });
        
        // Refresh leaderboard
        fetchLeaderboard();
      }
    } catch (error) {
      console.error('Error updating milestone:', error);
    }
  };

  const resetApp = () => {
    setCurrentStep('welcome');
    setUser(null);
    setAssessmentData({
      education_level: '',
      work_experience: '',
      current_role: '',
      target_role: '',
      industry: '',
      skills: [],
      timeline_months: 6,
      availability_hours_per_week: 10
    });
    setRoadmap(null);
  };

  const WelcomeScreen = () => (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 flex items-center justify-center p-4">
      <div className="max-w-4xl mx-auto text-center">
        <h1 className="text-6xl font-bold text-white mb-6 leading-tight">
          CareerPath <span className="text-cyan-400">AI</span>
        </h1>
        <p className="text-xl text-gray-300 mb-8 max-w-2xl mx-auto">
          Transform your career journey with AI-powered roadmaps, milestone tracking, 
          and a community of ambitious professionals
        </p>
        
        <div className="grid md:grid-cols-2 gap-8 mb-12">
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="text-4xl mb-4">🎯</div>
            <h3 className="text-xl font-semibold text-white mb-2">Smart Roadmaps</h3>
            <p className="text-gray-300">AI analyzes your background and goals to create personalized learning paths with actionable milestones</p>
          </div>
          
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="text-4xl mb-4">📈</div>
            <h3 className="text-xl font-semibold text-white mb-2">Progress Tracking</h3>
            <p className="text-gray-300">Track milestones, earn points, compete on leaderboards, and stay motivated with community support</p>
          </div>
        </div>
        
        <button 
          onClick={() => setCurrentStep('assessment')}
          className="bg-gradient-to-r from-cyan-500 to-blue-600 text-white px-8 py-4 rounded-xl text-lg font-semibold hover:from-cyan-600 hover:to-blue-700 transform hover:scale-105 transition-all duration-200 shadow-lg"
        >
          Start Your Career Journey →
        </button>
      </div>
    </div>
  );

  const AssessmentScreen = () => (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Career Assessment</h2>
          <p className="text-gray-600 mb-8">Help us understand your background and goals to create your personalized roadmap</p>
          
          <form onSubmit={handleAssessmentSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Education Level</label>
              <select 
                value={assessmentData.education_level} 
                onChange={(e) => setAssessmentData({...assessmentData, education_level: e.target.value})}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              >
                <option value="">Select education level</option>
                <option value="high_school">High School</option>
                <option value="bachelors">Bachelor's Degree</option>
                <option value="masters">Master's Degree</option>
                <option value="phd">PhD</option>
                <option value="bootcamp">Bootcamp/Certificate</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Work Experience</label>
              <select 
                value={assessmentData.work_experience} 
                onChange={(e) => setAssessmentData({...assessmentData, work_experience: e.target.value})}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              >
                <option value="">Select experience level</option>
                <option value="entry_level">Entry Level (0-2 years)</option>
                <option value="mid_level">Mid Level (3-5 years)</option>
                <option value="senior_level">Senior Level (6-10 years)</option>
                <option value="executive">Executive (10+ years)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Current Role (Optional)</label>
              <input 
                type="text"
                value={assessmentData.current_role} 
                onChange={(e) => setAssessmentData({...assessmentData, current_role: e.target.value})}
                placeholder="e.g., Marketing Associate, Software Developer"
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Target Role</label>
              <input 
                type="text"
                value={assessmentData.target_role} 
                onChange={(e) => setAssessmentData({...assessmentData, target_role: e.target.value})}
                placeholder="e.g., Product Manager, Senior Developer, Data Scientist"
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Industry</label>
              <select 
                value={assessmentData.industry} 
                onChange={(e) => setAssessmentData({...assessmentData, industry: e.target.value})}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              >
                <option value="">Select industry</option>
                <option value="technology">Technology</option>
                <option value="finance">Finance</option>
                <option value="healthcare">Healthcare</option>
                <option value="education">Education</option>
                <option value="marketing">Marketing</option>
                <option value="consulting">Consulting</option>
                <option value="retail">Retail</option>
                <option value="manufacturing">Manufacturing</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Current Skills</label>
              <input 
                type="text"
                value={assessmentData.skills.join(', ')} 
                onChange={(e) => setAssessmentData({...assessmentData, skills: e.target.value.split(',').map(s => s.trim()).filter(s => s)})}
                placeholder="e.g., Python, Project Management, Excel, Communication"
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <p className="text-sm text-gray-500 mt-1">Separate skills with commas</p>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Timeline (months)</label>
                <input 
                  type="number"
                  value={assessmentData.timeline_months} 
                  onChange={(e) => setAssessmentData({...assessmentData, timeline_months: parseInt(e.target.value)})}
                  min="1"
                  max="36"
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Hours per week</label>
                <input 
                  type="number"
                  value={assessmentData.availability_hours_per_week} 
                  onChange={(e) => setAssessmentData({...assessmentData, availability_hours_per_week: parseInt(e.target.value)})}
                  min="1"
                  max="40"
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
              </div>
            </div>

            <div className="flex gap-4">
              <button 
                type="button"
                onClick={() => setCurrentStep('welcome')}
                className="flex-1 bg-gray-200 text-gray-800 py-3 rounded-lg font-semibold hover:bg-gray-300 transition-colors"
              >
                Back
              </button>
              <button 
                type="submit"
                disabled={loading}
                className="flex-1 bg-gradient-to-r from-cyan-500 to-blue-600 text-white py-3 rounded-lg font-semibold hover:from-cyan-600 hover:to-blue-700 transition-all disabled:opacity-50"
              >
                {loading ? 'Generating Roadmap...' : 'Generate My Roadmap'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );

  const RoadmapScreen = () => (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2">{roadmap?.title}</h2>
              <p className="text-gray-600">{roadmap?.description}</p>
            </div>
            <button 
              onClick={resetApp}
              className="bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300 transition-colors"
            >
              New Assessment
            </button>
          </div>
          
          <div className="grid md:grid-cols-3 gap-4 mb-8">
            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{roadmap?.milestones?.length}</div>
              <div className="text-sm text-gray-600">Milestones</div>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-green-600">{roadmap?.total_estimated_hours}h</div>
              <div className="text-sm text-gray-600">Total Hours</div>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">
                {roadmap?.milestones?.filter(m => m.status === 'completed').length || 0}
              </div>
              <div className="text-sm text-gray-600">Completed</div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {roadmap?.milestones?.map((milestone, index) => (
            <div key={milestone.id} className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="bg-blue-100 text-blue-800 text-sm font-medium px-3 py-1 rounded-full">
                      Step {milestone.order}
                    </span>
                    <h3 className="text-xl font-semibold text-gray-900">{milestone.title}</h3>
                  </div>
                  <p className="text-gray-600 mb-3">{milestone.description}</p>
                  <div className="text-sm text-gray-500">
                    Estimated time: {milestone.estimated_hours} hours
                  </div>
                </div>
                
                <div className="flex gap-2 ml-4">
                  <button
                    onClick={() => updateMilestoneStatus(milestone.id, 'in_progress')}
                    className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                      milestone.status === 'in_progress' 
                        ? 'bg-yellow-100 text-yellow-800' 
                        : 'bg-gray-100 text-gray-600 hover:bg-yellow-100 hover:text-yellow-800'
                    }`}
                  >
                    In Progress
                  </button>
                  <button
                    onClick={() => updateMilestoneStatus(milestone.id, 'completed')}
                    className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                      milestone.status === 'completed' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-gray-100 text-gray-600 hover:bg-green-100 hover:text-green-800'
                    }`}
                  >
                    ✓ Completed
                  </button>
                </div>
              </div>
              
              {milestone.resources && milestone.resources.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Recommended Resources:</h4>
                  <div className="grid gap-2">
                    {milestone.resources.map((resource, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-sm">
                        <span className="text-blue-600">
                          {resource.type === 'course' ? '📚' : resource.type === 'book' ? '📖' : '🛠️'}
                        </span>
                        {resource.url ? (
                          <a href={resource.url} target="_blank" rel="noopener noreferrer" 
                             className="text-blue-600 hover:underline">
                            {resource.title}
                          </a>
                        ) : (
                          <span className="text-gray-700">{resource.title}</span>
                        )}
                        <span className="text-gray-400">({resource.type})</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {leaderboard.length > 0 && (
          <div className="bg-white rounded-xl shadow-lg p-8 mt-8">
            <h3 className="text-2xl font-bold text-gray-900 mb-6">Leaderboard</h3>
            <div className="space-y-3">
              {leaderboard.slice(0, 5).map((entry, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className="bg-blue-100 text-blue-800 w-8 h-8 rounded-full flex items-center justify-center font-semibold">
                      {entry.rank}
                    </span>
                    <span className="font-medium">{entry.user_name}</span>
                  </div>
                  <div className="text-sm text-gray-600">
                    {entry.total_points} points • {entry.milestones_completed} milestones
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="App">
      {currentStep === 'welcome' && <WelcomeScreen />}
      {currentStep === 'assessment' && <AssessmentScreen />}
      {currentStep === 'roadmap' && <RoadmapScreen />}
    </div>
  );
}

export default App;