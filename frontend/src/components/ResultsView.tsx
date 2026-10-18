import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Markdown from 'react-markdown';
import { ArrowLeft, Sparkles, CheckCircle, FileCode, BarChart3, Bot } from 'lucide-react';

interface ScoreItem {
  score_id: number;
  candidate_name: string;
  similarity_score: number;
}

function parseString(str: string) {
  return str.replace(/\n(?!\n)/g, '\n\n');  
}

export default function ResultsView() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [rawAssembly, setRawAssembly] = useState<string>("Loading assembly content...");
  const [llmOutput, setLlmOutput] = useState<string>("Loading LLM reasoning...");
  const [scores, setScores] = useState<ScoreItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Fetch data from your FastAPI backend using the input ID
  useEffect(() => {
    async function fetchData() {
      try {
        // 1. Fetch raw assembly input
        const inputRes = await fetch(`https://technica-2026-1.onrender.com/inputs/${id}`);
        if (inputRes.ok) {
          const inputData = await inputRes.json();
          setRawAssembly(inputData.raw_assembly || "No assembly text found.");
        }

        // 2. Fetch LLM output
        const outputRes = await fetch(`https://technica-2026-1.onrender.com/outputs/${id}`);
        if (outputRes.ok) {
          const outputData = await outputRes.json();
          setLlmOutput(outputData.llm_output || "No LLM output generated.");
        }

        // 3. Fetch Similarity Scores & handle potential type mismatches robustly
        const scoresRes = await fetch(`https://technica-2026-1.onrender.com/scores/${id}`);
        if (scoresRes.ok) {
          const scoresData = await scoresRes.json();
          
          let resolvedScores = scoresData.scores !== undefined ? scoresData.scores : scoresData;
          if (typeof resolvedScores === 'string') {
            try {
              resolvedScores = JSON.parse(resolvedScores);
            } catch (e) {
              console.error("Failed to load results data:", e);
              resolvedScores = [];
            }
          }
          
          setScores(Array.isArray(resolvedScores) ? resolvedScores : []);
        }
      } catch (err) {
        console.error("Failed to load results data:", err);
      } finally {
        setLoading(false);
      }
    }

    if (id) {
      fetchData();
    }
  }, [id]);

  return (
    <div className="min-h-screen bg-[#FDFBF7] text-stone-900 p-6 lg:p-12">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Top Bar / Navigation */}
        <div className="flex items-center justify-between pb-4 border-b border-stone-200">
          <button 
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-sm font-medium text-stone-600 hover:text-stone-900 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Upload
          </button>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full text-xs font-medium border border-emerald-200">
              <CheckCircle className="w-3.5 h-3.5" />
              Analysis Complete
            </span>
          </div>
        </div>

        {/* Main Split Layout: Left Content vs Right Stack */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          
          {/* LEFT COLUMN: Raw Assembly Text Preview */}
          <div className="lg:col-span-6 bg-white border border-stone-200/80 rounded-3xl p-6 lg:p-8 shadow-xl shadow-stone-200/40 flex flex-col h-[calc(100vh-14rem)]">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-stone-100">
              <h2 className="text-base font-serif font-medium text-stone-900 flex items-center gap-2">
                <FileCode className="w-4 h-4 text-orange-600" />
                Raw Assembly Input (.asm)
              </h2>
              <span className="text-xs text-stone-400 font-mono">Source Stream</span>
            </div>
            
            <div className="flex-1 bg-stone-900 text-stone-200 font-mono text-xs p-4 rounded-2xl overflow-y-auto leading-relaxed whitespace-pre-wrap select-text">
              {loading ? "Loading source..." : rawAssembly}
            </div>
          </div>

          {/* RIGHT COLUMN: Stacked Cards (Top: Scores, Bottom: LLM Result) */}
          <div className="lg:col-span-6 space-y-6">
            
            {/* UPPER RIGHT: Similarity Scores Table */}
            <div className="bg-white border border-stone-200/80 rounded-3xl p-6 lg:p-7 shadow-xl shadow-stone-200/40">
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-stone-100">
                <h3 className="text-base font-serif font-medium text-stone-900 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-orange-600" />
                  Structural Match Scores
                </h3>
                <span className="text-xs font-medium text-stone-500 bg-stone-100 px-2.5 py-1 rounded-lg">
                  Top Candidates
                </span>
              </div>

              <div className="max-h-[220px] overflow-y-auto pr-1">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-stone-200 text-xs font-semibold text-stone-500 uppercase tracking-wider">
                      <th className="py-2 px-3">Candidate</th>
                      <th className="py-2 px-3 text-right">Similarity</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-100">
                    {loading ? (
                      <tr>
                        <td colSpan={2} className="py-6 text-center text-xs text-stone-400">Loading similarity scores...</td>
                      </tr>
                    ) : scores.length > 0 ? (
                      scores.map((item) => (
                        <tr key={item.score_id} className="hover:bg-stone-50/80 transition-colors">
                          <td className="py-3 px-3 font-mono text-xs font-semibold text-stone-800">
                            {item.candidate_name}
                          </td>
                          <td className="py-3 px-3 text-right">
                            <div className="flex items-center justify-end gap-3">
                              <div className="w-20 bg-stone-200 h-1.5 rounded-full overflow-hidden hidden sm:block">
                                <div 
                                  className="bg-orange-600 h-full rounded-full" 
                                  style={{ width: `${item.similarity_score * 100}%` }}
                                ></div>
                              </div>
                              <span className="text-xs font-mono font-bold text-stone-700">
                                {(item.similarity_score * 100).toFixed(1)}%
                              </span>
                            </div>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={2} className="py-6 text-center text-xs text-stone-400">
                          No score records found for this input.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* LOWER RIGHT: LLM Reasoning Result (UPDATED FOR VERTICAL SCROLL) */}
            <div className="bg-white border border-stone-200/80 rounded-3xl p-6 lg:p-7 shadow-xl shadow-stone-200/40">
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-stone-100">
                <h3 className="text-base font-serif font-medium text-stone-900 flex items-center gap-2">
                  <Bot className="w-4 h-4 text-orange-600" />
                  Gemini Semantic Insight
                </h3>
                <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-orange-50 text-orange-700 rounded-lg text-xs font-medium border border-orange-200">
                  <Sparkles className="w-3 h-3" />
                  AI De-anonymized
                </span>
              </div>

              <div className="bg-stone-50 border border-stone-100 rounded-2xl p-4 text-sm text-stone-700 font-light leading-relaxed max-h-[220px] overflow-y-auto pr-1 custom-scrollbar prose prose-sm max-w-none prose-p:my-2">
                {loading ? "Generating reasoning insights..." : <Markdown>{parseString(llmOutput)}</Markdown>}
              </div>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
}