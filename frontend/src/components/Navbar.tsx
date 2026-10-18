import React from 'react';
import { Shield, ChevronDown, Globe } from 'lucide-react';

export default function Navbar() {
  return (
    <header className="w-full bg-[#FDFBF7] border-b border-stone-200/60 px-6 lg:px-16 py-4 sticky top-0 z-50 backdrop-blur-md bg-opacity-90">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        
        {/* Left side: Logo & Brand */}
        <div className="flex items-center gap-8">
          <a href="#" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 bg-orange-600 rounded-xl flex items-center justify-center text-white shadow-md shadow-orange-600/20 group-hover:bg-orange-700 transition-all">
              <Shield className="w-5 h-5" />
            </div>
            <span className="font-serif text-xl tracking-tight font-bold text-stone-900">
              PLACEHOLDER<span className="text-orange-600">.</span>
            </span>
          </a>

          {/* Navigation Links
          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-stone-600">
            <a href="#" className="flex items-center gap-1 hover:text-stone-900 transition-colors">
              Products <ChevronDown className="w-3.5 h-3.5 text-stone-400" />
            </a>
            <a href="#" className="flex items-center gap-1 hover:text-stone-900 transition-colors">
              Solutions <ChevronDown className="w-3.5 h-3.5 text-stone-400" />
            </a>
            <a href="#" className="flex items-center gap-1 hover:text-stone-900 transition-colors">
              Company <ChevronDown className="w-3.5 h-3.5 text-stone-400" />
            </a>
            <a href="#" className="flex items-center gap-1 hover:text-stone-900 transition-colors">
              Resources <ChevronDown className="w-3.5 h-3.5 text-stone-400" />
            </a>
            <a href="#" className="hover:text-stone-900 transition-colors">
              Pricing
            </a>
            <a href="#" className="text-orange-600 hover:text-orange-700 transition-colors">
              Contact Sales
            </a>
          </nav> */}
        </div>

        {/* Right side: Language, Login & CTA
        <div className="flex items-center gap-5">
          <button className="hidden sm:flex items-center gap-1.5 text-sm font-medium text-stone-600 hover:text-stone-900 transition-colors">
            <Globe className="w-4 h-4 text-stone-400" />
          </button>
          <a href="#" className="text-sm font-medium text-stone-900 hover:text-orange-600 transition-colors">
            Login
          </a>
          <button className="px-5 py-2.5 bg-orange-600 hover:bg-orange-700 text-white text-sm font-medium rounded-xl shadow-lg shadow-orange-600/20 transition-all">
            Try It for Free
          </button>
        </div> */}

      </div>
    </header>
  );
}