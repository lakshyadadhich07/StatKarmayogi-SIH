import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { Lightbulb, ExternalLink, ShieldAlert, GraduationCap } from 'lucide-react';
import { motion } from 'framer-motion';

const radarData = [
  { subject: 'Index Numbers', current: 85, target: 100, fullMark: 100 },
  { subject: 'National Accounts', current: 45, target: 80, fullMark: 100 },
  { subject: 'Sampling Tech', current: 30, target: 80, fullMark: 100 },
  { subject: 'Social Stats', current: 75, target: 90, fullMark: 100 },
  { subject: 'Demography', current: 65, target: 80, fullMark: 100 },
];

export default function GapAnalysis() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6">
      
      {/* Header / Summary Strip */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-navy mb-4 flex items-center">
          <Lightbulb className="w-8 h-8 mr-3 text-orange" />
          Gap Analysis & Recommendations
        </h1>
        
        <div className="bg-blue-steel/10 border border-blue-steel/20 rounded-xl p-4 flex items-center">
          <ShieldAlert className="w-5 h-5 text-blue-steel mr-3" />
          <p className="font-medium text-navy">
            <span className="font-bold text-blue-steel">2 gaps identified</span> • 2 iGOT courses recommended to reach Target Level
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Radar Chart */}
        <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-gray-100 flex flex-col h-full min-h-[450px]">
          <h2 className="text-xl font-semibold text-navy mb-6 text-center">Competency Radar</h2>
          <div className="flex-grow w-full h-full min-h-[350px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                <PolarGrid stroke="#e5e7eb" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: '#4b5563', fontSize: 13, fontWeight: 500 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  itemStyle={{ fontWeight: 600 }}
                />
                <Radar 
                  name="Target Level" 
                  dataKey="target" 
                  stroke="#9ca3af" 
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  fill="#f3f4f6" 
                  fillOpacity={0.3} 
                />
                <Radar 
                  name="Your Current Level" 
                  dataKey="current" 
                  stroke="#3B4B5C" 
                  strokeWidth={3}
                  fill="#3B4B5C" 
                  fillOpacity={0.5} 
                />
                <Legend wrapperStyle={{ paddingTop: '20px' }} iconType="circle" />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recommendations */}
        <div className="space-y-6 flex flex-col h-full justify-center">
          <h2 className="text-xl font-semibold text-navy mb-2">Recommended Learning Path</h2>
          
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white rounded-2xl p-6 shadow-sm border-l-4 border-l-orange border-y border-y-gray-100 border-r border-r-gray-100 hover:shadow-md transition-shadow relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 p-4 opacity-5">
              <GraduationCap className="w-24 h-24" />
            </div>
            <div className="relative z-10">
              <div className="flex justify-between items-start mb-2">
                <span className="bg-orange/10 text-orange font-bold px-3 py-1 rounded-full text-xs tracking-wide uppercase">Priority Gap</span>
                <span className="font-bold text-gray-400 text-sm">Score: 30 / 80</span>
              </div>
              <h3 className="text-xl font-bold text-navy mb-1">Sampling Techniques</h3>
              <p className="text-gray-600 text-sm mb-5 leading-relaxed">
                Your understanding of stratified and cluster sampling variance needs improvement for the upcoming NSSO field assignments.
              </p>
              
              <div className="bg-gray-50 rounded-xl p-4 border border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <p className="font-bold text-navy text-sm">iGOT Course #104</p>
                  <p className="font-medium text-green">Advanced Sampling Techniques</p>
                </div>
                <a href="#" className="inline-flex items-center justify-center bg-green hover:bg-green/90 text-white font-medium px-5 py-2.5 rounded-lg transition-colors text-sm whitespace-nowrap">
                  Open in iGOT
                  <ExternalLink className="w-4 h-4 ml-2" />
                </a>
              </div>
            </div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white rounded-2xl p-6 shadow-sm border-l-4 border-l-yellow-500 border-y border-y-gray-100 border-r border-r-gray-100 hover:shadow-md transition-shadow relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 p-4 opacity-5">
              <GraduationCap className="w-24 h-24" />
            </div>
            <div className="relative z-10">
              <div className="flex justify-between items-start mb-2">
                <span className="bg-yellow-500/10 text-yellow-700 font-bold px-3 py-1 rounded-full text-xs tracking-wide uppercase">Moderate Gap</span>
                <span className="font-bold text-gray-400 text-sm">Score: 45 / 80</span>
              </div>
              <h3 className="text-xl font-bold text-navy mb-1">National Accounts</h3>
              <p className="text-gray-600 text-sm mb-5 leading-relaxed">
                Refresh your knowledge on GDP calculation methodologies (Income vs Expenditure) used in current statistical frameworks.
              </p>
              
              <div className="bg-gray-50 rounded-xl p-4 border border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <p className="font-bold text-navy text-sm">iGOT Course #082</p>
                  <p className="font-medium text-green">National Income Estimation</p>
                </div>
                <a href="#" className="inline-flex items-center justify-center bg-green hover:bg-green/90 text-white font-medium px-5 py-2.5 rounded-lg transition-colors text-sm whitespace-nowrap">
                  Open in iGOT
                  <ExternalLink className="w-4 h-4 ml-2" />
                </a>
              </div>
            </div>
          </motion.div>

        </div>
      </div>

    </div>
  );
}
