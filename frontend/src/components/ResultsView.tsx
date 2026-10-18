import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Sparkles, CheckCircle, FileCode, BarChart3, Bot } from 'lucide-react';

interface ScoreItem {
  score_id: number;
  candidate_name: string;
  similarity_score: number;
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
        const inputRes = await fetch(`http://127.0.0.1:8000/inputs/${id}`);
        if (inputRes.ok) {
          const inputData = await inputRes.json();
          setRawAssembly(inputData.raw_assembly || "No assembly text found.");
        }

        // 2. Fetch LLM output
        const outputRes = await fetch(`http://127.0.0.1:8000/outputs/${id}`);
        if (outputRes.ok) {
          const outputData = await outputRes.json();
          setLlmOutput(outputData.llm_output || "No LLM output generated.");
        }

        // 3. Fetch Similarity Scores
        const scoresRes = await fetch(`http://127.0.0.1:8000/scores/${id}`);
        if (scoresRes.ok) {
          const scoresData = await scoresRes.json();
          setScores(scoresData.scores || []);
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
            <span className="text-xs font-mono bg-stone-100 border border-stone-200 px-3 py-1.5 rounded-xl text-stone-600">
              Input ID: <span className="font-bold text-stone-900">{id}</span>
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
            
            {/* UPPER RIGHT: Similarity Scores */}
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

              <div className="space-y-3 max-h-[200px] overflow-y-auto pr-1">
                {loading ? (
                  <p className="text-xs text-stone-400">Loading similarity scores...</p>
                ) : scores.length > 0 ? (
                  scores.map((item) => (
                    <div key={item.score_id} className="flex items-center justify-between p-3 bg-stone-50 border border-stone-100 rounded-xl">
                      <span className="text-sm font-semibold text-stone-800 font-mono">{item.candidate_name}</span>
                      <div className="flex items-center gap-3">
                        <div className="w-24 bg-stone-200 h-2 rounded-full overflow-hidden">
                          <div 
                            className="bg-orange-600 h-full rounded-full" 
                            style={{ width: `${item.similarity_score * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-xs font-mono font-bold text-stone-700">
                          {(item.similarity_score * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-stone-500">No score records found for this input.</p>
                )}
              </div>
            </div>

            {/* LOWER RIGHT: LLM Reasoning Result */}
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

              <div className="bg-stone-50 border border-stone-100 rounded-2xl p-4 text-sm text-stone-700 font-light leading-relaxed max-h-[220px] overflow-y-auto">
                {loading ? "Generating reasoning insights..." : llmOutput}
              </div>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
}