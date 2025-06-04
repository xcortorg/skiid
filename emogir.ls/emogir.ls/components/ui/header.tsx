"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "./button";
import { FaChevronDown } from "react-icons/fa";
import { RxDashboard } from "react-icons/rx";

export const Header = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="flex items-center justify-between px-6 py-6 relative max-w-7xl mx-auto w-full">
      <div>
        <Link href="/">
          <h1 className="text-2xl font-bold select-none">
            emogir<span className="text-[#ff3379] text-sm">.ls</span>
          </h1>
        </Link>
      </div>

      <div className="hidden sm:flex items-center gap-8">
        <Link href="/" className="text-sm font-medium text-white/80 hover:text-white transition-colors">
          Home
        </Link>
        <Link href="/features" className="text-sm font-medium text-white/80 hover:text-white transition-colors">
          Features
        </Link>
        <Link href="/pricing" className="text-sm font-medium text-white/80 hover:text-white transition-colors">
          Pricing
        </Link>
        <Link href="/about" className="text-sm font-medium text-white/80 hover:text-white transition-colors">
          About
        </Link>
      </div>

      <div className="hidden sm:block">
        <Button text="Dashboard" href="/login" icon={RxDashboard} />
      </div>

      <div className="flex text-primary sm:hidden">
        <FaChevronDown
          className={`transition-[0.3s] text-xl ${
            mobileMenuOpen ? "-rotate-180" : ""
          }`}
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        />
        <div
          className={`absolute top-20 right-4 rounded-lg bg-[#1a1a1a] border border-white/10 w-[calc(100%-2rem)] max-w-sm select-none text-base text-center z-[1000] p-4 ${
            mobileMenuOpen
              ? "flex flex-col gap-4 animate-in slide-in-from-top-4"
              : "hidden"
          }`}
        >
          <div className="flex flex-col gap-4 w-full">
            <Link
              href="/"
              className="text-sm font-medium text-white/80 hover:text-white transition-colors"
            >
              Home
            </Link>
            <Link
              href="#features"
              className="text-sm font-medium text-white/80 hover:text-white transition-colors"
            >
              Features
            </Link>
            <Link
              href="/pricing"
              className="text-sm font-medium text-white/80 hover:text-white transition-colors"
            >
              Pricing
            </Link>
            <Link
              href="/about"
              className="text-sm font-medium text-white/80 hover:text-white transition-colors"
            >
              About
            </Link>
          </div>
          <Button text="Dashboard" href="/login" icon={RxDashboard} className="w-full" />
        </div>
      </div>
    </header>
  );
};
