import React, { useState } from 'react';
import { useNavigate } from 'react-router';
import { Upload, FileCode, CheckCircle2, Sparkles, ArrowRight, ShieldCheck } from 'lucide-react';
import HowItWorks from './HowItWorks';
import ProductFeatures from './ProductFeatures';

export default function HeroSection() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);

  const navigate = useNavigate();

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUploadClick = async () => {
    if (!selectedFile) return;
    setLoading(true);

    try {
      const rawAssembly = await selectedFile.text();

      // Existing upload contract intentionally unchanged.
      const response = await fetch('https://technica-2026.onrender.com/run-pipeline', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ raw_assembly: rawAssembly }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to upload assembly content');
      }

      const data = await response.json();
      setLoading(false);
      alert(`Successfully saved! Input ID: ${data.input_id}`);

      if (data.input_id) {
        navigate(`/results/${data.input_id}`);
      } else {
        throw new Error('Backend response did not include an input_id.');
      }
    } catch (error: unknown) {
      console.error('Detailed error:', error);
      setLoading(false);

      let errorMessage = 'Failed to connect to backend';
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        errorMessage = error;
      }

      alert(`Backend Error: ${errorMessage}`);
    }
  };

  return (
    <>
      <section className="relative text-stone-900 flex items-center overflow-hidden px-6 lg:px-16 py-12 lg:py-20">
        <div className="max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-12 items-center relative z-10">
          {/* LEFT COLUMN: Value Proposition / Blurb */}
          <div className="lg:col-span-6 space-y-8">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-orange-50 border border-orange-200 rounded-full text-orange-700 text-xs font-semibold tracking-wide uppercase">
              <Sparkles className="w-3.5 h-3.5" />
              Algorithmic Code Intelligence
            </div>

            <h1 className="text-5xl lg:text-6xl font-serif tracking-tight leading-[1.1]">
              A binary de-anonymizer that <span className="italic font-normal">actually</span> works.
            </h1>

            <p className="text-lg text-stone-600 font-light leading-relaxed max-w-xl">
              Transform stripped assembly binaries into clear algorithmic insights instantly.
              Powered by structural model embeddings and Gemini semantic reasoning.
            </p>

            <div className="flex flex-wrap items-center gap-4">
              <button className="px-6 py-3 bg-orange-600 hover:bg-orange-700 text-white font-medium rounded-xl shadow-lg shadow-orange-600/20 transition-all flex items-center gap-2">
                Try It for Free
                <ArrowRight className="w-4 h-4" />
              </button>
              <button className="px-6 py-3 bg-orange-100/60 hover:bg-orange-100 text-orange-900 font-medium rounded-xl transition-all">
                View Documentation
              </button>
            </div>

            <div className="pt-6 border-t border-stone-200 flex items-center gap-4 text-xs text-stone-500">
              <ShieldCheck className="w-8 h-8 text-stone-700 shrink-0" />
              <p>Built for high-precision reverse engineering, malware triage, and automated code archaeology.</p>
            </div>
          </div>

          {/* RIGHT COLUMN: Existing upload workspace */}
          <div className="lg:col-span-6">
            <div className="bg-white/80 backdrop-blur-xl border border-stone-200/80 rounded-3xl p-6 lg:p-8 shadow-2xl shadow-stone-200/50 relative">
              <div className="flex items-center justify-between mb-6 pb-4 border-b border-stone-100">
                <div className="flex items-center gap-2 bg-stone-100 p-1 rounded-xl">
                  <button className="px-4 py-1.5 text-xs font-semibold bg-white text-stone-900 rounded-lg shadow-sm">
                    .ASM Upload
                  </button>
                </div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 text-emerald-700 rounded-full text-xs font-medium border border-emerald-200">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  System Online
                </span>
              </div>

              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all flex flex-col items-center justify-center min-h-[220px] ${
                  isDragging ? 'border-orange-500 bg-orange-50/50' : 'border-stone-200 bg-stone-50/50 hover:bg-stone-50'
                }`}
              >
                {selectedFile ? (
                  <div className="flex flex-col items-center space-y-3">
                    <div className="w-12 h-12 bg-orange-100 text-orange-600 rounded-xl flex items-center justify-center">
                      <FileCode className="w-6 h-6" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-stone-800">{selectedFile.name}</p>
                      <p className="text-xs text-stone-500">{(selectedFile.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button onClick={() => setSelectedFile(null)} className="text-xs text-red-600 hover:underline mt-1">
                      Remove file
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col items-center space-y-3">
                    <div className="w-12 h-12 bg-white shadow-sm border border-stone-200 text-stone-600 rounded-xl flex items-center justify-center">
                      <Upload className="w-5 h-5 text-orange-600" />
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-stone-800">
                        Drop your binary or{' '}
                        <label className="text-orange-600 cursor-pointer hover:underline">
                          browse
                          <input type="file" onChange={handleFileChange} className="hidden" accept=".asm,.bin,.txt" />
                        </label>
                      </p>
                      <p className="text-xs text-stone-400">Supports raw assembly (.asm) or binary formats</p>
                    </div>
                  </div>
                )}
              </div>

              <div className="mt-6 flex items-center justify-end gap-3 pt-4 border-t border-stone-100">
                <button
                  disabled={!selectedFile || loading}
                  onClick={handleUploadClick}
                  className={`w-full py-3 px-6 rounded-xl font-medium text-white transition-all flex items-center justify-center gap-2 shadow-lg ${
                    !selectedFile || loading
                      ? 'bg-stone-300 cursor-not-allowed shadow-none'
                      : 'bg-stone-900 hover:bg-stone-800 shadow-stone-900/20'
                  }`}
                >
                  {loading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Running Inference Pipeline...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      Upload &amp; Run De-anonymizer
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Both homepage sections are independent components. */}
      <HowItWorks />
      <ProductFeatures />
    </>
  );
}
