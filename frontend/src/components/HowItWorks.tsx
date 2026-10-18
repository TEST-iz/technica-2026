import { useState } from 'react';
import {
  BrainCircuit,
  FileCode2,
  ListFilter,
  Minus,
  Plus,
} from 'lucide-react';

type Step = {
  title: string;
  description: string;
};

const STEPS: Step[] = [
  {
    title: 'Upload your code',
    description: 'Start with a supported compiled program or function.',
  },
  {
    title: 'Extract program structure',
    description:
      'Recover instructions, basic blocks, and the paths connecting them.',
  },
  {
    title: 'Learn structural patterns',
    description:
      'A graph neural network turns the function into a learned embedding.',
  },
  {
    title: 'Find similar algorithms',
    description:
      'Compare against indexed references and explore the closest candidate matches.',
  },
];

const SAMPLE_ASSEMBLY = [
  'push rbp',
  'mov rbp, rsp',
  'cmp eax, 0',
  'jne 0x401028',
  '...',
];

const VECTOR_HEIGHTS = [48, 24, 64, 40, 72, 32, 56, 16, 48, 32, 64, 24, 40, 72, 32, 48, 56, 24, 64, 40];

const SAMPLE_MATCHES = [
  { id: '206', similarity: '0.86' },
  { id: '92', similarity: '0.62' },
  { id: '24', similarity: '0.41' },
];

function CodePreview() {
  return (
    <div className="flex w-full max-w-sm flex-col items-center gap-4">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-orange-100 bg-orange-50 text-orange-600">
        <FileCode2 className="h-6 w-6" aria-hidden="true" />
      </div>
      <div className="w-full overflow-hidden rounded-xl border border-stone-200 bg-[#F7F5F1]">
        <div className="border-b border-stone-200 px-4 py-2 font-mono text-[10px] uppercase tracking-wider text-stone-500">
          unknown_function
        </div>
        <pre className="overflow-x-auto px-4 py-4 text-left font-mono text-xs leading-6 text-stone-700">
          <code>{SAMPLE_ASSEMBLY.join('\n')}</code>
        </pre>
      </div>
    </div>
  );
}

function GraphPreview() {
  return (
    <div className="flex w-full flex-col items-center gap-3">
      <svg
        className="h-56 w-full max-w-[370px]"
        viewBox="0 0 320 220"
        role="img"
        aria-label="Illustrative control-flow graph: entry leads to a decision, branching to two blocks that both lead to return"
      >
        <defs>
          <marker id="codetrace-cfg-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M0 0 L10 5 L0 10 Z" fill="#A8A29E" />
          </marker>
        </defs>
        <g stroke="#A8A29E" strokeWidth="2" fill="none" markerEnd="url(#codetrace-cfg-arrow)">
          <path d="M160 44 V69" />
          <path d="M132 115 L85 145" />
          <path d="M188 115 L235 145" />
          <path d="M85 172 L145 199" />
          <path d="M235 172 L175 199" />
        </g>
        <rect x="122" y="12" width="76" height="32" rx="9" fill="#F5F5F4" stroke="#D6D3D1" />
        <rect x="110" y="71" width="100" height="44" rx="10" fill="#FFEDD5" stroke="#EA580C" />
        <rect x="42" y="145" width="86" height="28" rx="8" fill="#F5F5F4" stroke="#D6D3D1" />
        <rect x="192" y="145" width="86" height="28" rx="8" fill="#F5F5F4" stroke="#D6D3D1" />
        <rect x="124" y="197" width="72" height="21" rx="7" fill="#F5F5F4" stroke="#D6D3D1" />
        <g fill="#44403C" fontFamily="ui-sans-serif, system-ui, sans-serif" fontSize="12" textAnchor="middle">
          <text x="160" y="32">Entry</text>
          <text x="160" y="97" fontWeight="600">Branch</text>
          <text x="85" y="163">Block A</text>
          <text x="235" y="163">Block B</text>
          <text x="160" y="212" fontSize="10">Return</text>
        </g>
      </svg>
      <p className="text-center text-xs text-stone-500">Illustrative control-flow graph</p>
    </div>
  );
}

function EmbeddingPreview() {
  return (
    <div className="flex w-full flex-col items-center gap-5">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-orange-100 bg-orange-50 text-orange-600">
        <BrainCircuit className="h-6 w-6" aria-hidden="true" />
      </div>
      <div className="flex h-28 w-full max-w-sm items-center justify-center gap-1.5 rounded-xl bg-[#F7F5F1] px-4" aria-label="Decorative illustration of a vector embedding">
        {VECTOR_HEIGHTS.map((height, index) => (
          <span
            key={index}
            className={`w-1.5 shrink-0 rounded-sm ${index % 3 === 0 ? 'bg-[#EAA26E]' : 'bg-[#C55E24]'}`}
            style={{ height: `${height}px` }}
          />
        ))}
      </div>
      <div className="text-center">
        <p className="font-medium text-stone-700">Function embedding</p>
        <p className="mt-1 text-xs text-stone-500">Illustrative numerical representation</p>
      </div>
    </div>
  );
}

function ResultsPreview() {
  return (
    <div className="flex w-full max-w-sm flex-col items-center gap-4">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-orange-100 bg-orange-50 text-orange-600">
        <ListFilter className="h-6 w-6" aria-hidden="true" />
      </div>
      <div className="w-full space-y-2">
        {SAMPLE_MATCHES.map((item, index) => (
          <div key={item.id} className={`flex items-center justify-between rounded-lg border px-4 py-3 text-sm ${index === 0 ? 'border-orange-200 bg-orange-50' : 'border-stone-200 bg-[#F7F5F1]'}`}>
            <span className="font-medium text-stone-700">Problem #{item.id}</span>
            <span className="font-mono font-semibold tabular-nums text-orange-700">{item.similarity}</span>
          </div>
        ))}
      </div>
      <p className="text-center text-xs text-stone-500">Illustrative rankings, not model predictions</p>
    </div>
  );
}

const PREVIEWS = [CodePreview, GraphPreview, EmbeddingPreview, ResultsPreview];

export default function HowItWorks() {
  const [activeStep, setActiveStep] = useState(1);
  const Preview = PREVIEWS[activeStep];

  return (
    <section id="how-it-works" aria-labelledby="how-it-works-title" className="bg-[#FAF9F6] px-6 py-20 text-stone-900 lg:px-16 lg:py-28">
      <div className="mx-auto max-w-7xl">
        <div className="mb-10 max-w-4xl lg:mb-14">
          <p className="mb-5 inline-flex items-center border-l-2 border-orange-500 bg-orange-100/60 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.13em] text-orange-700">
            How It Works
          </p>
          <h2 id="how-it-works-title" className="font-serif text-4xl font-normal leading-[1.12] tracking-tight sm:text-5xl lg:text-6xl">
            From machine code to <span className="italic">meaningful matches.</span>
          </h2>
          <p className="mt-6 max-w-3xl text-base font-light leading-relaxed text-stone-600 sm:text-lg">
            CodeTrace analyzes program structure, learns numerical representations of compiled functions, and searches for similar implementations.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2 lg:gap-8">
          <div className="flex flex-col rounded-3xl bg-[#F0EDE7] p-5 sm:p-7">
            <div className="mb-5 flex items-center justify-between gap-3">
              <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-stone-500">CodeTrace / Analysis</span>
              <span className="font-mono text-xs font-medium text-orange-700">{String(activeStep + 1).padStart(2, '0')} / 04</span>
            </div>
            <div className="flex min-h-[310px] flex-1 items-center justify-center rounded-2xl border border-stone-200 bg-white p-5 shadow-sm sm:min-h-[360px] sm:p-8" aria-live="polite" aria-atomic="true">
              <Preview />
            </div>
          </div>

          <div className="flex flex-col gap-3">
            {STEPS.map((step, index) => {
              const expanded = index === activeStep;
              return (
                <button
                  key={step.title}
                  type="button"
                  aria-expanded={expanded}
                  aria-controls={`codetrace-how-step-${index}`}
                  onClick={() => setActiveStep(index)}
                  className={`flex min-h-[84px] flex-col rounded-2xl border p-5 text-left transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500 focus-visible:ring-offset-2 sm:p-6 ${expanded ? 'border-orange-200 bg-white shadow-sm' : 'border-transparent bg-[#F0EDE7] hover:border-stone-300 hover:bg-white/70'}`}
                >
                  <span className="flex w-full items-center justify-between gap-3">
                    <span className="flex items-center gap-4">
                      <span className="font-mono text-sm font-medium text-orange-700">{String(index + 1).padStart(2, '0')}</span>
                      <span className="text-base font-semibold tracking-tight text-stone-800 sm:text-lg">{step.title}</span>
                    </span>
                    {expanded ? <Minus className="h-4 w-4 shrink-0 text-orange-700" aria-hidden="true" /> : <Plus className="h-4 w-4 shrink-0 text-orange-700" aria-hidden="true" />}
                  </span>
                  <span id={`codetrace-how-step-${index}`} className={expanded ? 'mt-3 pl-9 text-sm leading-relaxed text-stone-600' : 'hidden'}>
                    {step.description}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}