"use client";

import React from "react";

export function SignatureIllustration() {
  return (
    <div className="relative mx-auto flex w-full max-w-lg items-center justify-center p-4 lg:max-w-none">
      <svg
        viewBox="0 0 640 520"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="h-auto w-full select-none"
        aria-label="Illustration: Translucent resume transforming into a path toward career opportunity"
        role="img"
      >
        <defs>
          {/* Subtle Ambient Radial Glow */}
          <radialGradient
            id="ambientGlow"
            cx="50%"
            cy="45%"
            r="60%"
            fx="50%"
            fy="45%"
          >
            <stop offset="0%" stopColor="#5477B8" stopOpacity="0.12" />
            <stop offset="60%" stopColor="#9CA6B2" stopOpacity="0.04" />
            <stop offset="100%" stopColor="transparent" stopOpacity="0" />
          </radialGradient>

          {/* Translucent Frosted Glass Resume Face */}
          <linearGradient
            id="glassResumeFace"
            x1="120"
            y1="60"
            x2="320"
            y2="340"
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.75" />
            <stop offset="40%" stopColor="#D9E0E6" stopOpacity="0.45" />
            <stop offset="100%" stopColor="#9CA6B2" stopOpacity="0.25" />
          </linearGradient>

          {/* Chrome Beveled Border */}
          <linearGradient
            id="chromeBevel"
            x1="120"
            y1="60"
            x2="320"
            y2="340"
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.9" />
            <stop offset="25%" stopColor="#9CA6B2" stopOpacity="0.7" />
            <stop offset="50%" stopColor="#5477B8" stopOpacity="0.8" />
            <stop offset="75%" stopColor="#D9E0E6" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#181A1D" stopOpacity="0.3" />
          </linearGradient>

          {/* Liquid Glass Ribbon Body */}
          <linearGradient
            id="liquidRibbon"
            x1="220"
            y1="300"
            x2="520"
            y2="180"
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0%" stopColor="#D9E0E6" stopOpacity="0.3" />
            <stop offset="35%" stopColor="#5477B8" stopOpacity="0.45" />
            <stop offset="70%" stopColor="#9CA6B2" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#5477B8" stopOpacity="0.6" />
          </linearGradient>

          {/* Liquid Ribbon Chrome Highlight Spine */}
          <linearGradient
            id="ribbonSpine"
            x1="220"
            y1="300"
            x2="520"
            y2="180"
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.8" />
            <stop offset="50%" stopColor="#6E90D1" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#5477B8" stopOpacity="0.9" />
          </linearGradient>

          {/* Architectural Opportunity Portal Gradient */}
          <linearGradient
            id="portalGlow"
            x1="460"
            y1="120"
            x2="560"
            y2="280"
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0%" stopColor="#5477B8" stopOpacity="0.8" />
            <stop offset="50%" stopColor="#6E90D1" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#9CA6B2" stopOpacity="0.1" />
          </linearGradient>

          {/* Frosted drop shadow filter */}
          <filter id="glassBlur" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow
              dx="4"
              dy="16"
              stdDeviation="16"
              floodColor="#181A1D"
              floodOpacity="0.10"
            />
          </filter>
        </defs>

        {/* Background Atmosphere */}
        <circle cx="320" cy="260" r="240" fill="url(#ambientGlow)" />

        {/* 1. Abstract Architectural Symbol of Opportunity (Right Composition) */}
        <g id="opportunityPortal">
          {/* Subtle radiating signal beams */}
          <line
            x1="520"
            y1="150"
            x2="590"
            y2="100"
            stroke="#5477B8"
            strokeOpacity="0.25"
            strokeWidth="1.5"
            strokeDasharray="4 4"
          />
          <line
            x1="520"
            y1="170"
            x2="610"
            y2="170"
            stroke="#5477B8"
            strokeOpacity="0.3"
            strokeWidth="1.5"
            strokeDasharray="4 4"
          />
          <line
            x1="520"
            y1="190"
            x2="595"
            y2="240"
            stroke="#5477B8"
            strokeOpacity="0.25"
            strokeWidth="1.5"
            strokeDasharray="4 4"
          />

          {/* Outer Gateway Arch */}
          <path
            d="M 470 290 L 470 180 C 470 135, 550 135, 550 180 L 550 290"
            stroke="url(#portalGlow)"
            strokeWidth="2.5"
            strokeLinecap="round"
          />

          {/* Inner Opportunity Beacon (Architectural Keystones) */}
          <path
            d="M 488 290 L 488 190 C 488 155, 532 155, 532 190 L 532 290"
            stroke="#9CA6B2"
            strokeOpacity="0.4"
            strokeWidth="1.5"
          />

          {/* Horizon Line Accent */}
          <line
            x1="440"
            y1="290"
            x2="580"
            y2="290"
            stroke="#9CA6B2"
            strokeOpacity="0.35"
            strokeWidth="1.5"
          />

          {/* Ascending Stepping Planes */}
          <polygon
            points="495,280 525,280 535,274 505,274"
            fill="#5477B8"
            fillOpacity="0.45"
          />
          <polygon
            points="500,260 520,260 528,255 508,255"
            fill="#5477B8"
            fillOpacity="0.65"
          />
          <polygon
            points="505,240 515,240 520,236 510,236"
            fill="#6E90D1"
            fillOpacity="0.85"
          />
        </g>

        {/* 2. Graceful Liquid-Glass Ribbon (Directional Movement) */}
        <g id="liquidRibbonGroup">
          {/* Translucent ribbon sweep from resume base to opportunity portal */}
          <path
            d="M 235 315 C 270 340, 310 380, 370 350 C 430 320, 440 230, 495 240 C 510 242, 515 250, 520 270 C 495 275, 430 365, 360 380 C 290 395, 240 330, 235 315 Z"
            fill="url(#liquidRibbon)"
          />

          {/* Chrome reflection spine along the primary ribbon curve */}
          <path
            d="M 235 315 C 270 340, 310 380, 370 350 C 430 320, 440 230, 495 240"
            stroke="url(#ribbonSpine)"
            strokeWidth="2.5"
            strokeLinecap="round"
          />

          {/* Secondary subtle water/glass caustic line */}
          <path
            d="M 245 325 C 280 350, 320 385, 375 360 C 425 335, 435 255, 480 255"
            stroke="#FFFFFF"
            strokeOpacity="0.4"
            strokeWidth="1"
            strokeDasharray="6 3"
          />
        </g>

        {/* 3. The Translucent Resume Sheet (Main Recognizable Object) */}
        {/* Subtle isometric tilt: top-left (140, 70), top-right (300, 105), bottom-right (260, 350), bottom-left (100, 315) */}
        <g id="translucentResume" filter="url(#glassBlur)">
          {/* Main Resume Surface Plate */}
          <polygon
            points="140,70 300,105 260,350 100,315"
            fill="url(#glassResumeFace)"
            stroke="url(#chromeBevel)"
            strokeWidth="2"
          />

          {/* Resume Header Elements (Candidate Identity Block) */}
          {/* Avatar / Monogram Pill */}
          <polygon
            points="128,100 152,105 148,125 124,120"
            fill="#5477B8"
            fillOpacity="0.4"
          />
          {/* Name Bar */}
          <polygon
            points="162,104 228,118 226,126 160,112"
            fill="#181A1D"
            fillOpacity="0.5"
            className="dark:fill-white dark:fill-opacity-60"
          />
          {/* Subtitle / Title Bar */}
          <polygon
            points="161,116 205,125 204,130 160,121"
            fill="#9CA6B2"
            fillOpacity="0.6"
          />

          {/* Divider rule */}
          <line
            x1="120"
            y1="135"
            x2="280"
            y2="170"
            stroke="#9CA6B2"
            strokeOpacity="0.35"
            strokeWidth="1"
          />

          {/* Section 1: Experience Bullets */}
          {/* Section Header */}
          <polygon
            points="120,147 170,158 169,164 119,153"
            fill="#5477B8"
            fillOpacity="0.7"
          />

          {/* Bullet 1 */}
          <circle cx="124" cy="168" r="2" fill="#5477B8" fillOpacity="0.7" />
          <polygon
            points="132,166 265,195 264,199 131,170"
            fill="#58616D"
            fillOpacity="0.45"
            className="dark:fill-[#A0ABB8]"
          />
          <polygon
            points="132,174 240,197 239,201 131,178"
            fill="#58616D"
            fillOpacity="0.35"
            className="dark:fill-[#A0ABB8]"
          />

          {/* Bullet 2 */}
          <circle cx="120" cy="189" r="2" fill="#5477B8" fillOpacity="0.7" />
          <polygon
            points="128,187 255,214 254,218 127,191"
            fill="#58616D"
            fillOpacity="0.45"
            className="dark:fill-[#A0ABB8]"
          />
          <polygon
            points="128,195 220,215 219,219 127,199"
            fill="#58616D"
            fillOpacity="0.35"
            className="dark:fill-[#A0ABB8]"
          />

          {/* Section 2: Skills Pills (Bottom Section) */}
          <polygon
            points="114,218 154,226 153,232 113,224"
            fill="#5477B8"
            fillOpacity="0.7"
          />
          {/* Skill Tag 1 */}
          <polygon
            points="113,234 148,241 146,251 111,244"
            fill="#5477B8"
            fillOpacity="0.2"
            stroke="#5477B8"
            strokeOpacity="0.4"
            strokeWidth="0.8"
          />
          {/* Skill Tag 2 */}
          <polygon
            points="154,242 195,250 193,260 152,252"
            fill="#5477B8"
            fillOpacity="0.2"
            stroke="#5477B8"
            strokeOpacity="0.4"
            strokeWidth="0.8"
          />
          {/* Skill Tag 3 */}
          <polygon
            points="201,252 245,261 243,271 199,262"
            fill="#5477B8"
            fillOpacity="0.2"
            stroke="#5477B8"
            strokeOpacity="0.4"
            strokeWidth="0.8"
          />

          {/* Translucent Corner Reflection Gleam */}
          <polygon
            points="141,71 180,80 160,130 115,100"
            fill="#FFFFFF"
            fillOpacity="0.15"
          />
        </g>
      </svg>
    </div>
  );
}
