"use client";

import Image from "next/image";
import Link from "next/link";

import { cn } from "@/lib/utils";

type BrandLogoVariant = "lockup" | "mark" | "wordmark" | "compact";

interface BrandLogoProps {
  variant?: BrandLogoVariant;
  href?: string | null;
  className?: string;
  priority?: boolean;
}

/** AeroVantage mark + wordmark — brand sheet assets under /public/brand */
export function BrandLogo({
  variant = "compact",
  href = "/",
  className,
  priority = false,
}: BrandLogoProps) {
  const content =
    variant === "lockup" ? (
      <Image
        src="/brand/logo-lockup.png"
        alt="AeroVantage"
        width={288}
        height={51}
        priority={priority}
        className="h-7 w-auto max-w-full bg-transparent object-contain object-left"
      />
    ) : variant === "mark" ? (
      <Image
        src="/brand/logo-mark.png"
        alt="AeroVantage"
        width={40}
        height={36}
        priority={priority}
        className="h-7 w-auto bg-transparent object-contain"
      />
    ) : variant === "wordmark" ? (
      <Image
        src="/brand/wordmark.png"
        alt="AeroVantage — Operational Intelligence"
        width={220}
        height={42}
        priority={priority}
        className="h-8 w-auto max-w-full bg-transparent object-contain object-left"
      />
    ) : (
      <span className="flex min-w-0 items-center gap-2">
        <Image
          src="/brand/logo-mark.png"
          alt=""
          width={28}
          height={26}
          priority={priority}
          className="h-[22px] w-auto shrink-0 bg-transparent object-contain"
          aria-hidden
        />
        <span className="min-w-0 leading-none">
          <span className="block truncate text-[11px] font-semibold tracking-[0.14em] text-zinc-50">
            ΛEROVΛNTΛGE
          </span>
          <span className="mt-0.5 block truncate text-[8px] font-medium tracking-[0.18em] text-[#00D1B2]">
            OPERATIONAL INTELLIGENCE
          </span>
        </span>
      </span>
    );

  const classes = cn("inline-flex items-center bg-transparent", className);

  if (href) {
    return (
      <Link href={href} className={classes} aria-label="AeroVantage">
        {content}
      </Link>
    );
  }

  return <span className={classes}>{content}</span>;
}
