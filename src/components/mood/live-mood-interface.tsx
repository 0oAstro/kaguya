"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Webcam from "react-webcam";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import TextAnimate from "@/components/ui/text-animate";
import QRCode from "qrcode";
import {
  Camera,
  CameraOff,
  Sparkles,
  Music,
  Download,
  Share2,
  QrCode,
  Play,
  Pause,
  RefreshCw,
} from "lucide-react";

interface MoodResponse {
  mood: string;
  confidence: number;
  playlist_url?: string;
  recommendations: Array<{
    name: string;
    artist: string;
    preview_url?: string;
  }>;
}

interface VideoState {
  isActive: boolean;
  isProcessing: boolean;
  error: string | null;
}

export default function LiveMoodInterface() {
  const webcamRef = useRef<Webcam>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const detectionEnabledRef = useRef<boolean>(true);

  const [videoState, setVideoState] = useState<VideoState>({
    isActive: false,
    isProcessing: false,
    error: null,
  });

  const [moodResult, setMoodResult] = useState<MoodResponse | null>(null);
  const [showResults, setShowResults] = useState(false);
  const [currentMood, setCurrentMood] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number>(0);
  const [qrCode, setQrCode] = useState<string>("");
  const [playlistGenerated, setPlaylistGenerated] = useState(false);
  const [playlistFixed, setPlaylistFixed] = useState(false);


  // Capture photo and detect mood with instant playlist creation
  const captureAndDetectMood = useCallback(async () => {
    if (!webcamRef.current || videoState.isProcessing || !detectionEnabledRef.current) return;

    try {
      setVideoState(prev => ({ ...prev, isProcessing: true }));

      // Capture screenshot from webcam
      const imageSrc = webcamRef.current.getScreenshot();
      if (!imageSrc) {
        throw new Error("Failed to capture image");
      }

      // Convert data URL to base64 (remove data:image/jpeg;base64, prefix)
      const base64Image = imageSrc.split(",")[1];

      // Create mood and playlist instantly
      const response = await fetch("/api/mood-and-playlist", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ image_base64: base64Image }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to detect mood");
      }

      const result: MoodResponse = await response.json();
      
      // Update current mood display
      setCurrentMood(result.mood);
      setConfidence(result.confidence);
      
      // Store full result with playlist
      setMoodResult(result);

      // Generate QR code instantly if we have a real playlist URL
      if (result.playlist_url && result.playlist_url.includes('open.spotify.com/playlist/')) {
        const qr = await QRCode.toDataURL(result.playlist_url);
        setQrCode(qr);
        setPlaylistFixed(true);
        console.log('✅ Real playlist QR code generated instantly:', result.playlist_url);
      } else {
        setQrCode('');
        console.log('⚠️ No real playlist created - continuing detection');
      }

      console.log('📱 Mood detected with playlist:', result.mood);

    } catch (error) {
      console.error("Error detecting mood:", error);
      setVideoState(prev => ({ 
        ...prev, 
        error: error instanceof Error ? error.message : "Failed to detect mood"
      }));
    } finally {
      setVideoState(prev => ({ ...prev, isProcessing: false }));
    }
  }, [videoState.isProcessing]);



  // Start camera
  const startCamera = useCallback(() => {
    setVideoState(prev => ({ ...prev, isActive: true, error: null }));
    detectionEnabledRef.current = true;
    
    // Start mood detection every 3 seconds
    intervalRef.current = setInterval(() => {
      captureAndDetectMood();
    }, 3000);
  }, []);

  // Stop camera
  const stopCamera = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    setVideoState(prev => ({ ...prev, isActive: false }));
    setCurrentMood(null);
    setConfidence(0);
  }, []);

  // Auto-start camera on mount
  useEffect(() => {
    startCamera();
    return () => stopCamera();
  }, [startCamera, stopCamera]);

  const handleGetPlaylist = () => {
    if (moodResult) {
      setPlaylistGenerated(true);
      setShowResults(true);
    }
  };

  const handleShare = async () => {
    if (moodResult?.playlist_url) {
      try {
        await navigator.share({
          title: `My ${moodResult.mood} mood playlist`,
          text: `Check out this ${moodResult.mood} playlist curated for my current mood!`,
          url: moodResult.playlist_url,
        });
      } catch (error) {
        // Fallback to clipboard
        await navigator.clipboard.writeText(moodResult.playlist_url);
        alert("Playlist URL copied to clipboard!");
      }
    }
  };

  const getMoodColor = (mood: string) => {
    const colors: Record<string, string> = {
      happy: "text-white",
      sad: "text-gray-400", 
      energetic: "text-white",
      calm: "text-gray-300",
      excited: "text-white",
      relaxed: "text-gray-300",
      melancholic: "text-gray-400",
    };
    return colors[mood] || "text-gray-400";
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-12">
        <div className="max-w-3xl mx-auto">
          {/* Header */}
          <div className="text-center mb-6">
            <TextAnimate
              text="live mood detection"
              className="text-2xl font-bold text-white mb-1"
              type="fadeInUp"
            />
            <TextAnimate
              text="ai analyzes your emotions in real-time"
              className="text-xs text-muted-foreground"
              type="calmInUp"
              delay={0.2}
            />
          </div>

          {/* Main Interface */}
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-white" />
                live camera feed
                {playlistFixed && <span className="text-green-400">playlist ready</span>}
                {playlistGenerated && !playlistFixed && <span className="text-blue-400">processing</span>}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Video Feed */}
              <div className="relative aspect-video bg-black rounded-lg overflow-hidden border border-border">
                {videoState.isActive ? (
                  <>
                    <Webcam
                      ref={webcamRef}
                      audio={false}
                      width={640}
                      height={480}
                      mirrored={true}
                      screenshotFormat="image/jpeg"
                      videoConstraints={{
                        width: 640,
                        height: 480,
                        facingMode: "user"
                      }}
                      className="w-full h-full object-cover"
                    />
                    
                    {/* Live Mood Overlay */}
                    {currentMood && (
                      <div className="absolute top-3 left-3 bg-black/80 backdrop-blur rounded-lg p-2 border border-white/20">
                        <div className="flex items-center gap-2 mb-1">
                          <div className={`w-2 h-2 rounded-full ${playlistFixed ? 'bg-green-500' : playlistGenerated ? 'bg-blue-500' : 'bg-red-500 animate-pulse'}`} />
                          <span className="text-xs text-white">{playlistFixed ? 'playlist ready' : playlistGenerated ? 'done' : 'live'}</span>
                        </div>
                        <div className={`font-semibold text-sm ${getMoodColor(currentMood)}`}>
                          {currentMood.toLowerCase()}
                        </div>
                        <div className="text-xs text-gray-300">
                          {Math.round(confidence * 100)}%
                        </div>
                      </div>
                    )}

                    {/* Processing Indicator */}
                    {videoState.isProcessing && (
                      <div className="absolute top-3 right-3 bg-black/80 backdrop-blur rounded-lg p-2">
                        <RefreshCw className="h-3 w-3 text-white animate-spin" />
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full space-y-3">
                    <CameraOff className="h-12 w-12 text-muted-foreground" />
                    <div className="text-center">
                      <p className="text-sm font-medium mb-1">camera not active</p>
                      <p className="text-xs text-muted-foreground">
                        click start camera to begin
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Error Display */}
              {videoState.error && (
                <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                  <p className="text-destructive">{videoState.error}</p>
                </div>
              )}

              {/* Controls */}
              <div className="flex justify-center gap-2">
                {!videoState.isActive ? (
                  <Button
                    onClick={startCamera}
                    size="sm"
                    className="bg-white text-black hover:bg-gray-100 font-medium px-3 py-1 rounded transition-all"
                  >
                    <Camera className="h-4 w-4 mr-1" />
                    start camera
                  </Button>
                ) : (
                  <>
                    <Button
                      onClick={stopCamera}
                      variant="outline"
                      size="sm"
                      className="border border-white/20 text-white hover:bg-white/10 font-medium px-3 py-1 rounded transition-all"
                    >
                      <CameraOff className="h-4 w-4 mr-1" />
                      stop
                    </Button>
                    
                    {moodResult && !playlistGenerated && (
                      <Button
                        onClick={handleGetPlaylist}
                        size="sm"
                        className="bg-white text-black hover:bg-gray-100 font-medium px-3 py-1 rounded transition-all"
                      >
                        <Music className="h-4 w-4 mr-1" />
                        get playlist
                      </Button>
                    )}
                    

                    
                    {playlistGenerated && (
                      <div className="flex items-center gap-1 px-2 py-1 bg-white/10 border border-white/20 rounded">
                        <span className="text-white text-xs">ready</span>
                      </div>
                    )}
                  </>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Results Dialog */}
          <Dialog open={showResults} onOpenChange={(open) => {
            setShowResults(open);
            if (!open) {
              // When dialog is closed, restart mood detection
              console.log('🔄 Dialog closed, restarting mood detection...');
              setPlaylistGenerated(false);
              setPlaylistFixed(false);
              setQrCode('');
              setMoodResult(null);
              setCurrentMood(null);
              setConfidence(0);
              
              // Enable detection
              detectionEnabledRef.current = true;
              
              // Restart detection if camera is active and no interval running
              if (videoState.isActive && !intervalRef.current) {
                console.log('🔄 Starting detection interval...');
                intervalRef.current = setInterval(() => {
                  captureAndDetectMood();
                }, 3000);
                // Also trigger immediate detection
                setTimeout(() => captureAndDetectMood(), 500);
              }
            } else {
              // Dialog opened - disable detection
              console.log('⏸️ Dialog opened, pausing detection...');
              detectionEnabledRef.current = false;
            }
          }}>
            <DialogContent className="max-w-[90vw] w-[90vw] max-h-[90vh] overflow-hidden">
              <DialogHeader className="pb-6">
                <DialogTitle>your playlist</DialogTitle>
              </DialogHeader>
              
              {moodResult && (
                <div className="space-y-8">
                  {/* Center Focus: Mood + Big QR Code */}
                  <div className="flex flex-col items-center space-y-6">
                    {/* Mood Result Above QR */}
                    <div className="text-center space-y-3">
                      <div className={`text-5xl font-bold ${getMoodColor(moodResult.mood)}`}>
                        {moodResult.mood.toLowerCase()}
                      </div>
                      <Progress value={moodResult.confidence * 100} className="w-64 h-3" />
                      <p className="text-lg text-muted-foreground">
                        {Math.round(moodResult.confidence * 100)}% confidence • {moodResult.recommendations.length} songs
                      </p>
                    </div>

                    {/* Big QR Code - Main Focus */}
                    {qrCode && (
                      <div className="flex flex-col items-center space-y-4">
                        <div className="p-6 bg-white rounded-xl shadow-xl">
                          <img src={qrCode} alt="playlist qr code" className="w-64 h-64" />
                        </div>
                        <p className="text-lg text-muted-foreground text-center font-medium">
                          scan to open your playlist
                        </p>
                      </div>
                    )}
                  </div>


                </div>
              )}
            </DialogContent>
          </Dialog>
        </div>
      </div>
    </div>
  );
}
