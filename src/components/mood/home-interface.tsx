"use client";

import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Camera, Music } from "lucide-react";

export default function HomeInterface() {
  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
      <div className="container mx-auto px-4">
        <div className="max-w-2xl mx-auto text-center">
          {/* Jigglypuff */}
          <div className="flex justify-center mb-12">
            <Image
              src="/jigglypuff.png"
              alt="Jigglypuff"
              width={300}
              height={300}
              className="pixel-art"
            />
          </div>
          
          {/* Title */}
          <h1 className="text-4xl font-bold text-white mb-4">
            get me my playlist
          </h1>
          
          <p className="text-lg text-muted-foreground mb-12">
            ai-powered mood detection and music curation
          </p>

          {/* Get Playlist Button */}
          <div className="flex justify-center">
            <Button 
              asChild
              className="bg-white text-black hover:bg-gray-100 font-medium px-12 py-4 rounded-lg transition-all duration-200 text-lg"
            >
              <Link href="/live">
                <Music className="h-6 w-6 mr-3" />
                get playlist
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
