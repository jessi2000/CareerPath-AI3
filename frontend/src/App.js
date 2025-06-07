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
      // First create a user profile
      const userName = assessmentData.target_role ? 
        `Future ${assessmentData.target_role}` : 'Career Seeker';
      
      const userProfile = {
        name: userName,
        email: `user${Date.now()}@careerpath.ai`,
        ...assessmentData
      };
      
      const userResponse = await fetch(`${API_BASE}/api/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userProfile),
      });
      
      if (!userResponse.ok) {
        throw new Error('Failed to create user profile');
      }
      
      const userData = await userResponse.json();
      setUser(userData);
      
      // Generate roadmap using AI
      const roadmapResponse = await fetch(`${API_BASE}/api/generate-roadmap?user_name=${encodeURIComponent(userName)}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(assessmentData),
      });
      
      if (!roadmapResponse.ok) {
        throw new Error('Failed to generate roadmap');
      }
      
      const generatedRoadmap = await roadmapResponse.json();
      
      // Save the roadmap to the database with user ID
      generatedRoadmap.user_id = userData.id;
      
      const saveResponse = await fetch(`${API_BASE}/api/roadmaps`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(generatedRoadmap),
      });
      
      if (!saveResponse.ok) {
        throw new Error('Failed to save roadmap');
      }
      
      const savedRoadmap = await saveResponse.json();
      setRoadmap(savedRoadmap);
      setCurrentStep('roadmap');
      
      // Refresh leaderboard to include new user
      fetchLeaderboard();
      
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
        const result = await response.json();
        
        // Update local roadmap state
        const updatedMilestones = roadmap.milestones.map(m => 
          m.id === milestoneId ? { ...m, status } : m
        );
        setRoadmap({ ...roadmap, milestones: updatedMilestones, progress_percentage: result.progress_percentage });
        
        // Show success message for completion
        if (status === 'completed') {
          alert('🎉 Milestone completed! You earned 10 points!');
        }
        
        // Refresh leaderboard
        fetchLeaderboard();
      } else {
        throw new Error('Failed to update milestone status');
      }
    } catch (error) {
      console.error('Error updating milestone:', error);
      alert('Failed to update milestone status. Please try again.');
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

  const AssessmentScreen = () => {
  // Use local state for input values to prevent focus loss
  const [localInputs, setLocalInputs] = useState({
    education_level: assessmentData.education_level,
    work_experience: assessmentData.work_experience,
    current_role: assessmentData.current_role,
    target_role: assessmentData.target_role,
    industry: assessmentData.industry,
    skills: assessmentData.skills.join(', '),
    timeline_months: assessmentData.timeline_months,
    availability_hours_per_week: assessmentData.availability_hours_per_week
  });

  // Update assessment data only when form is submitted
  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Convert skills string to array
    const skillsArray = localInputs.skills.split(',').map(s => s.trim()).filter(s => s.length > 0);
    
    // Update the main state with all form values
    setAssessmentData({
      education_level: localInputs.education_level,
      work_experience: localInputs.work_experience,
      current_role: localInputs.current_role,
      target_role: localInputs.target_role,
      industry: localInputs.industry,
      skills: skillsArray,
      timeline_months: localInputs.timeline_months,
      availability_hours_per_week: localInputs.availability_hours_per_week
    });
    
    // Call the original submit handler
    handleAssessmentSubmit(e);
  };

  // Handle local input changes without triggering re-renders
  const handleInputChange = (field, value) => {
    setLocalInputs({
      ...localInputs,
      [field]: value
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white/10 backdrop-blur-sm rounded-xl shadow-lg p-8 border border-white/20">
          <h2 className="text-3xl font-bold text-white mb-2">Career Assessment</h2>
          <p className="text-gray-300 mb-8">Help us understand your background and goals to create your personalized roadmap</p>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Education Level</label>
              <select 
                value={localInputs.education_level} 
                onChange={(e) => handleInputChange('education_level', e.target.value)}
                className="w-full p-3 border border-white/30 bg-white/20 text-white rounded-lg focus:ring-2 focus:ring-cyan-400 focus:border-transparent placeholder-gray-300"
                required
              >
                <option value="" className="text-gray-900">Select education level</option>
                <option value="high_school" className="text-gray-900">High School</option>
                <option value="bachelors" className="text-gray-900">Bachelor's Degree</option>
                <option value="masters" className="text-gray-900">Master's Degree</option>
                <option value="phd" className="text-gray-900">PhD</option>
                <option value="bootcamp" className="text-gray-900">Bootcamp/Certificate</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Work Experience</label>
              <select 
                value={localInputs.work_experience} 
                onChange={(e) => handleInputChange('work_experience', e.target.value)}
                className="w-full p-3 border border-white/30 bg-white/20 text-white rounded-lg focus:ring-2 focus:ring-cyan-400 focus:border-transparent placeholder-gray-300"
                required
              >
                <option value="" className="text-gray-900">Select experience level</option>
                <option value="entry_level" className="text-gray-900">Entry Level (0-2 years)</option>
                <option value="mid_level" className="text-gray-900">Mid Level (3-5 years)</option>
                <option value="senior_level" className="text-gray-900">Senior Level (6-10 years)</option>
                <option value="executive" className="text-gray-900">Executive (10+ years)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Current Role (Optional)</label>
              <input 
                type="text"
                value={localInputs.current_role} 
                onChange={(e) => handleInputChange('current_role', e.target.value)}
                placeholder="e.g., Marketing Associate, Software Developer"
                className="w-full p-3 border border-white/30 bg-white/20 text-white rounded-lg focus:ring-2 focus:ring-cyan-400 focus:border-transparent placeholder-gray-300"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Target Role</label>
              <input 
                type="text"
                value={localInputs.target_role} 
                onChange={(e) => handleInputChange('target_role', e.target.value)}
                placeholder="e.g., Product Manager, Senior Developer, Data Scientist"
                className="w-full p-3 border border-white/30 bg-white/20 text-white rounded-lg focus:ring-2 focus:ring-cyan-400 focus:border-transparent placeholder-gray-300"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Industry</label>
              <select 
                value={localInputs.industry} 
                onChange={(e) => handleInputChange('industry', e.target.value)}
                className="w-full p-3 border border-white/30 bg-white/20 text-white rounded-lg focus:ring-2 focus:ring-cyan-400 focus:border-transparent placeholder-gray-300"
                required
              >
                <option value="" className="text-gray-900">Select industry</option>
                <option value="technology" className="text-gray-900">Technology</option>
                <option value="finance" className="text-gray-900">Finance</option>
                <option value="healthcare" className="text-gray-900">Healthcare</option>
                <option value="education" className="text-gray-900">Education</option>
                <option value="marketing" className="text-gray-900">Marketing</option>
                <option value="consulting" className="text-gray-900">Consulting</option>
                <option value="retail" className="text-gray-900">Retail</option>
                <option value="manufacturing" className="text-gray-900">Manufacturing</option>
                <option value="other" className="text-gray-900">Other</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Current Skills</label>
              <input 
                type="text"
                value={localInputs.skills} 
                onChange={(e) => handleInputChange('skills', e.target.value)}
                placeholder="e.g., Python, Project Management, Excel, Communication"
                className="w-full p-3 border border-white/30 bg-white/20 text-white rounded-lg focus:ring-2 focus:ring-cyan-400 focus:border-transparent placeholder-gray-300"
              />
              <p className="text-sm text-gray-400 mt-1">Separate skills with commas</p>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Timeline (months)</label>
                <input 
                  type="number"
                  value={localInputs.timeline_months} 
                  onChange={(e) => {
                    const value = e.target.value;
                    if (value === '' || (!isNaN(value) && parseInt(value) >= 1 && parseInt(value) <= 36)) {
                      handleInputChange('timeline_months', value === '' ? 1 : parseInt(value));
                    }
                  }}
                  min="1"
                  max="36"
                  className="w-full p-3 border border-white/30 bg-white/20 text-white rounded-lg focus:ring-2 focus:ring-cyan-400 focus:border-transparent placeholder-gray-300"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Hours per week</label>
                <input 
                  type="number"
                  value={localInputs.availability_hours_per_week} 
                  onChange={(e) => {
                    const value = e.target.value;
                    if (value === '' || (!isNaN(value) && parseInt(value) >= 1 && parseInt(value) <= 40)) {
                      handleInputChange('availability_hours_per_week', value === '' ? 1 : parseInt(value));
                    }
                  }}
                  min="1"
                  max="40"
                  className="w-full p-3 border border-white/30 bg-white/20 text-white rounded-lg focus:ring-2 focus:ring-cyan-400 focus:border-transparent placeholder-gray-300"
                  required
                />
              </div>
            </div>

            <div className="flex gap-4">
              <button 
                type="button"
                onClick={() => setCurrentStep('welcome')}
                className="flex-1 bg-white/20 text-white py-3 rounded-lg font-semibold hover:bg-white/30 transition-colors border border-white/30"
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
};

  const RoadmapScreen = () => (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-indigo-900 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="bg-gray-800/80 backdrop-blur-sm rounded-xl shadow-lg p-8 mb-8 border border-gray-700">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-3xl font-bold text-white mb-2">{roadmap?.title}</h2>
              <p className="text-gray-300 mb-3">{roadmap?.description}</p>
              {roadmap?.market_context && (
                <div className="bg-blue-900/50 border-l-4 border-blue-400 p-4 mb-3 rounded-r-lg">
                  <h4 className="font-semibold text-blue-300 mb-1">Current Market Context</h4>
                  <p className="text-blue-200 text-sm">{roadmap.market_context}</p>
                </div>
              )}
              {roadmap?.current_market_salary && (
                <div className="bg-green-900/50 border-l-4 border-green-400 p-4 mb-3 rounded-r-lg">
                  <h4 className="font-semibold text-green-300 mb-1">Expected Salary Range</h4>
                  <p className="text-green-200 text-sm">{roadmap.current_market_salary}</p>
                </div>
              )}
              {user && (
                <p className="text-sm text-cyan-400 mt-2">Welcome, {user.name}!</p>
              )}
            </div>
            <button 
              onClick={resetApp}
              className="bg-gray-700 text-gray-200 px-4 py-2 rounded-lg hover:bg-gray-600 transition-colors border border-gray-600"
            >
              New Assessment
            </button>
          </div>
          
          {/* Progress Bar */}
          <div className="mb-6">
            <div className="flex justify-between text-sm text-gray-300 mb-2">
              <span>Overall Progress</span>
              <span>{Math.round((roadmap?.milestones?.filter(m => m.status === 'completed').length || 0) / (roadmap?.milestones?.length || 1) * 100)}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-3">
              <div 
                className="bg-gradient-to-r from-green-400 to-green-600 h-3 rounded-full transition-all duration-500"
                style={{
                  width: `${(roadmap?.milestones?.filter(m => m.status === 'completed').length || 0) / (roadmap?.milestones?.length || 1) * 100}%`
                }}
              ></div>
            </div>
          </div>
          
          <div className="grid md:grid-cols-3 gap-4 mb-8">
            <div className="bg-blue-900/50 p-4 rounded-lg border border-blue-700">
              <div className="text-2xl font-bold text-blue-400">{roadmap?.milestones?.length}</div>
              <div className="text-sm text-gray-300">Milestones</div>
            </div>
            <div className="bg-green-900/50 p-4 rounded-lg border border-green-700">
              <div className="text-2xl font-bold text-green-400">{roadmap?.total_estimated_hours}h</div>
              <div className="text-sm text-gray-300">Total Hours</div>
            </div>
            <div className="bg-purple-900/50 p-4 rounded-lg border border-purple-700">
              <div className="text-2xl font-bold text-purple-400">
                {roadmap?.milestones?.filter(m => m.status === 'completed').length || 0}
              </div>
              <div className="text-sm text-gray-300">Completed</div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {roadmap?.milestones?.map((milestone, index) => (
            <div key={milestone.id} 
                 className={`bg-gray-800/80 backdrop-blur-sm rounded-xl shadow-lg p-6 border-l-4 transition-all duration-300 border border-gray-700 ${
                   milestone.status === 'completed' ? 'border-l-green-500 bg-green-900/20' :
                   milestone.status === 'in_progress' ? 'border-l-yellow-500 bg-yellow-900/20' :
                   'border-l-gray-500'
                 }`}>
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`text-sm font-medium px-3 py-1 rounded-full ${
                      milestone.status === 'completed' ? 'bg-green-900/50 text-green-300 border border-green-700' :
                      milestone.status === 'in_progress' ? 'bg-yellow-900/50 text-yellow-300 border border-yellow-700' :
                      'bg-blue-900/50 text-blue-300 border border-blue-700'
                    }`}>
                      Step {milestone.order}
                    </span>
                    <h3 className="text-xl font-semibold text-white">{milestone.title}</h3>
                    {milestone.status === 'completed' && (
                      <span className="text-green-400 text-xl">✅</span>
                    )}
                    {milestone.status === 'in_progress' && (
                      <span className="text-yellow-400 text-xl">🔄</span>
                    )}
                  </div>
                  <p className="text-gray-300 mb-3">{milestone.description}</p>
                  {milestone.market_relevance && (
                    <div className="bg-indigo-900/50 border-l-2 border-indigo-400 p-3 mb-3 rounded-r-lg">
                      <p className="text-indigo-300 text-sm font-medium">2025 Market Relevance:</p>
                      <p className="text-indigo-200 text-sm">{milestone.market_relevance}</p>
                    </div>
                  )}
                  <div className="text-sm text-gray-400">
                    Estimated time: {milestone.estimated_hours} hours
                  </div>
                </div>
                
                <div className="flex gap-2 ml-4">
                  <button
                    onClick={() => updateMilestoneStatus(milestone.id, 'in_progress')}
                    disabled={milestone.status === 'completed'}
                    className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                      milestone.status === 'in_progress' 
                        ? 'bg-yellow-900/50 text-yellow-300 border border-yellow-700' 
                        : milestone.status === 'completed'
                        ? 'bg-gray-700 text-gray-500 cursor-not-allowed border border-gray-600'
                        : 'bg-gray-700 text-gray-300 hover:bg-yellow-900/50 hover:text-yellow-300 border border-gray-600 hover:border-yellow-700'
                    }`}
                  >
                    {milestone.status === 'in_progress' ? '🔄 In Progress' : 'Start'}
                  </button>
                  <button
                    onClick={() => updateMilestoneStatus(milestone.id, 'completed')}
                    className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                      milestone.status === 'completed' 
                        ? 'bg-green-900/50 text-green-300 border border-green-700' 
                        : 'bg-gray-700 text-gray-300 hover:bg-green-900/50 hover:text-green-300 border border-gray-600 hover:border-green-700'
                    }`}
                  >
                    {milestone.status === 'completed' ? '✅ Completed' : 'Complete'}
                  </button>
                </div>
              </div>
              
              {milestone.resources && milestone.resources.length > 0 && (
                <div>
                  <h4 className="font-medium text-white mb-3">Verified Current Resources (2025):</h4>
                  <div className="grid gap-3">
                    {milestone.resources.map((resource, idx) => (
                      <div key={idx} className="bg-gray-750/50 p-3 rounded-lg border border-gray-600">
                        <div className="flex items-start gap-3">
                          <span className="text-lg flex-shrink-0 mt-1">
                            {resource.type === 'course' ? '📚' : 
                             resource.type === 'book' ? '📖' : 
                             resource.type === 'certification' ? '🏆' : '🛠️'}
                          </span>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              {resource.url ? (
                                <a href={resource.url} target="_blank" rel="noopener noreferrer" 
                                   className="font-medium text-cyan-400 hover:text-cyan-300 hover:underline">
                                  {resource.title}
                                </a>
                              ) : (
                                <span className="font-medium text-white">{resource.title}</span>
                              )}
                              <span className="text-xs bg-blue-900/50 text-blue-300 px-2 py-1 rounded-full border border-blue-700">
                                {resource.type}
                              </span>
                            </div>
                            <div className="text-sm text-gray-400 space-x-3">
                              {resource.provider && <span>Provider: {resource.provider}</span>}
                              {resource.cost && <span>Cost: {resource.cost}</span>}
                              {resource.rating && <span>Rating: {resource.rating}</span>}
                              {resource.duration && <span>Duration: {resource.duration}</span>}
                              {resource.author && <span>Author: {resource.author}</span>}
                              {resource.year && <span>Year: {resource.year}</span>}
                            </div>
                            {resource.description && (
                              <p className="text-sm text-gray-300 mt-1">{resource.description}</p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {roadmap?.success_metrics && (
          <div className="bg-gray-800/80 backdrop-blur-sm rounded-xl shadow-lg p-8 mt-8 border border-gray-700">
            <h3 className="text-2xl font-bold text-white mb-4">Success Metrics & Goals</h3>
            <div className="bg-purple-900/50 border-l-4 border-purple-400 p-4 rounded-r-lg">
              <p className="text-purple-200">{roadmap.success_metrics}</p>
            </div>
          </div>
        )}

        {leaderboard.length > 0 && (
          <div className="bg-gray-800/80 backdrop-blur-sm rounded-xl shadow-lg p-8 mt-8 border border-gray-700">
            <h3 className="text-2xl font-bold text-white mb-6">Leaderboard</h3>
            <div className="space-y-3">
              {leaderboard.slice(0, 5).map((entry, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-gray-750/50 rounded-lg border border-gray-600">
                  <div className="flex items-center gap-3">
                    <span className="bg-blue-900/50 text-blue-300 w-8 h-8 rounded-full flex items-center justify-center font-semibold border border-blue-700">
                      {entry.rank}
                    </span>
                    <span className="font-medium text-white">{entry.user_name}</span>
                  </div>
                  <div className="text-sm text-gray-400">
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