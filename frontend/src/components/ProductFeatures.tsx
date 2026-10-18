import { ListOrdered, Network, ScanSearch, Search } from 'lucide-react';

const SAMPLE_MATCHES = [
  { id: '206', similarity: '0.86' },
  { id: '92', similarity: '0.62' },
  { id: '24', similarity: '0.41' },
];

function SearchMockup() {
  return (
    <div className="flex min-h-[215px] items-center justify-center p-5 sm:p-7">
      <div className="w-full max-w-sm rounded-2xl border border-white/70 bg-white p-4 shadow-lg shadow-amber-900/10">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-stone-500">Function Search</span>
          <ScanSearch className="h-4 w-4 text-orange-600" aria-hidden="true" />
        </div>
        <pre className="overflow-hidden rounded-lg bg-stone-100 px-3 py-3 font-mono text-[11px] leading-5 text-stone-700"><code>{'mov eax, [rbp-4]\ncmp eax, 0\njne 0x401080'}</code></pre>
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-orange-50 p-2.5 text-xs text-orange-800">
          <Search className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>Find matching patterns</span>
        </div>
      </div>
    </div>
  );
}

function GraphMockup() {
  return (
    <div className="flex min-h-[215px] items-center justify-center p-5 sm:p-7">
      <div className="w-full max-w-sm rounded-2xl border border-white/70 bg-white p-4 shadow-lg shadow-purple-900/10">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-stone-500">Control Flow</span>
          <Network className="h-4 w-4 text-purple-600" aria-hidden="true" />
        </div>
        <svg className="mx-auto mt-3 h-[142px] w-full max-w-[240px]" viewBox="0 0 240 150" role="img" aria-label="Illustrative control-flow graph with two paths joining at an exit">
          <defs>
            <marker id="codetrace-feature-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
              <path d="M0 0 L10 5 L0 10 Z" fill="#AB8DB9" />
            </marker>
          </defs>
          <g stroke="#AB8DB9" strokeWidth="2" fill="none" markerEnd="url(#codetrace-feature-arrow)">
            <path d="M120 28 V47" />
            <path d="M120 71 L65 90" />
            <path d="M120 71 L175 90" />
            <path d="M65 111 L120 131" />
            <path d="M175 111 L120 131" />
          </g>
          <rect x="82" y="4" width="76" height="24" rx="7" fill="#F4E7F6" stroke="#C6A5D1" />
          <rect x="75" y="47" width="90" height="24" rx="7" fill="#E2C6EC" stroke="#B583C8" />
          <rect x="35" y="90" width="60" height="21" rx="6" fill="#F4E7F6" stroke="#C6A5D1" />
          <rect x="145" y="90" width="60" height="21" rx="6" fill="#F4E7F6" stroke="#C6A5D1" />
          <circle cx="120" cy="134" r="9" fill="#9C67AD" />
          <g fontFamily="ui-sans-serif, system-ui, sans-serif" fontSize="10" textAnchor="middle" fill="#674378">
            <text x="120" y="20">Entry</text>
            <text x="120" y="63">Branch</text>
            <text x="65" y="104">Block A</text>
            <text x="175" y="104">Block B</text>
          </g>
        </svg>
      </div>
    </div>
  );
}

function MatchesMockup() {
  return (
    <div className="flex min-h-[215px] items-center justify-center p-5 sm:p-7">
      <div className="w-full max-w-sm rounded-2xl border border-white/70 bg-[#FFFDF9] p-4 shadow-lg shadow-black/15">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-stone-500">Similarity Results</span>
          <ListOrdered className="h-4 w-4 text-orange-600" aria-hidden="true" />
        </div>
        <div className="space-y-2">
          {SAMPLE_MATCHES.map((item, index) => (
            <div key={item.id} className={`flex items-center justify-between rounded-lg px-3 py-2.5 text-xs ${index === 0 ? 'bg-orange-50' : 'bg-stone-100'}`}>
              <span className="font-medium text-stone-700">Problem #{item.id}</span>
              <span className={`font-mono font-semibold tabular-nums ${index === 0 ? 'text-orange-700' : 'text-stone-500'}`}>{item.similarity}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function ProductFeatures() {
  return (
    <section id="our-product" aria-labelledby="product-features-title" className="bg-[#FAF9F6] px-6 pb-20 pt-12 text-stone-900 lg:px-16 lg:pb-28 lg:pt-16">
      <div className="mx-auto max-w-7xl">
        <div className="mb-10 max-w-4xl lg:mb-14">
          <p className="mb-5 inline-flex items-center border-l-2 border-orange-500 bg-orange-100/60 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.13em] text-orange-700">
            Our Product
          </p>
          <h2 id="product-features-title" className="font-serif text-4xl font-normal leading-[1.12] tracking-tight sm:text-5xl lg:text-6xl">
            Explore unfamiliar code with <span className="italic">CodeTrace.</span>
          </h2>
          <p className="mt-6 max-w-3xl text-base font-light leading-relaxed text-stone-600 sm:text-lg">
            Find familiar implementations, visualize control flow, and inspect the evidence behind every match.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3 md:gap-5 lg:gap-6">
          <article className="group flex flex-col overflow-hidden rounded-2xl bg-[#F2DD86] transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-amber-900/10">
            <SearchMockup />
            <div className="flex flex-1 flex-col gap-3 px-6 pb-7 pt-3 sm:px-7 sm:pb-9">
              <h3 className="font-serif text-3xl leading-tight text-[#342719] lg:text-[2.15rem]">Algorithm Search</h3>
              <p className="max-w-md text-sm leading-6 text-[#66512E]">Search compiled functions against a library of known implementations.</p>
            </div>
          </article>

          <article className="group flex flex-col overflow-hidden rounded-2xl bg-[#E9C2F1] transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-purple-900/10">
            <GraphMockup />
            <div className="flex flex-1 flex-col gap-3 px-6 pb-7 pt-3 sm:px-7 sm:pb-9">
              <h3 className="font-serif text-3xl leading-tight text-[#412648] lg:text-[2.15rem]">Graph Explorer</h3>
              <p className="max-w-md text-sm leading-6 text-[#664F6D]">Examine branches, loops, and the structure of recovered functions.</p>
            </div>
          </article>

          <article className="group flex flex-col overflow-hidden rounded-2xl bg-[#533019] transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-black/15">
            <MatchesMockup />
            <div className="flex flex-1 flex-col gap-3 px-6 pb-7 pt-3 sm:px-7 sm:pb-9">
              <h3 className="font-serif text-3xl leading-tight text-white lg:text-[2.15rem]">Match Inspection</h3>
              <p className="max-w-md text-sm leading-6 text-[#EDDACB]">Review ranked candidate problems and their supporting references.</p>
            </div>
          </article>
        </div>

        <p className="mt-5 text-xs text-stone-500">
          Preview data is illustrative. Actual search results are produced by the connected analysis pipeline.
        </p>
      </div>
    </section>
  );
}