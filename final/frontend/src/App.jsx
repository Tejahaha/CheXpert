import React, { useState, useRef, useCallback } from "react";
import {
  Upload,
  Activity,
  AlertCircle,
  Stethoscope,
  FileImage,
  Trash2,
  Heart,
  Shield,
  Zap,
  CheckCircle2,
  Target,
  Eye,
  Info,
  ChevronRight,
  MessageSquare,
  Send,
  Volume2,
} from "lucide-react";
import { Routes, Route, Link, useLocation } from "react-router-dom";
import About from "./About";

const CLASS_COLORS = {
  "Aortic enlargement": "#f43f5e",
  "Atelectasis": "#f97316",
  "Calcification": "#eab308",
  "Cardiomegaly": "#ef4444",
  "Consolidation": "#a855f7",
  "ILD": "#ec4899",
  "Infiltration": "#14b8a6",
  "Lung Opacity": "#6366f1",
  "Nodule/Mass": "#f59e0b",
  "Other lesion": "#8b5cf6",
  "Pleural effusion": "#06b6d4",
  "Pleural thickening": "#84cc16",
  "Pneumothorax": "#e11d48",
  "Pulmonary fibrosis": "#0ea5e9",
};

function getColor(name) {
  return CLASS_COLORS[name] || "#64748b";
}

function BBoxOverlay({ detections, imgWidth, imgHeight }) {
  if (!detections || detections.length === 0) return null;

  return (
    <svg
      className="bbox-svg"
      viewBox={`0 0 ${imgWidth} ${imgHeight}`}
      preserveAspectRatio="none"
    >
      {detections.map((det, i) => {
        const { x_min, y_min, x_max, y_max } = det.bbox;
        const color = getColor(det.class_name);
        const w = x_max - x_min;
        const h = y_max - y_min;
        return (
          <g key={i}>
            <rect
              x={x_min}
              y={y_min}
              width={w}
              height={h}
              fill="none"
              stroke={color}
              strokeWidth={Math.max(imgWidth * 0.003, 2)}
              rx={3}
            />
            <rect
              x={x_min}
              y={Math.max(y_min - 22, 0)}
              width={Math.max(det.class_name.length * 8 + 40, 80)}
              height={22}
              fill={color}
              rx={3}
            />
            <text
              x={x_min + 4}
              y={Math.max(y_min - 6, 16)}
              fill="#fff"
              fontSize={13}
              fontWeight="600"
              fontFamily="Inter, sans-serif"
            >
              {det.class_name} {(det.confidence * 100).toFixed(0)}%
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function DetectionCard({ det, index }) {
  const color = getColor(det.class_name);
  const confidencePercent = (det.confidence * 100).toFixed(1);

  return (
    <div className="detection-item" style={{ borderLeftColor: color }}>
      <div className="det-header">
        <span className="det-index" style={{ backgroundColor: color }}>
          {index + 1}
        </span>
        <span className="det-name">{det.class_name}</span>
        <span className="det-conf" style={{ color: color }}>
          {confidencePercent}%
        </span>
      </div>
      <div className="det-bar-track">
        <div
          className="det-bar-fill"
          style={{
            width: `${confidencePercent}%`,
            backgroundColor: color,
          }}
        />
      </div>
    </div>
  );
}

function AudioPlayer({ src }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef(null);

  const togglePlay = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
    } else {
      // Pause all other audio elements on the page before playing this one
      const allAudios = document.querySelectorAll('audio');
      allAudios.forEach(audio => {
        if (audio !== audioRef.current && !audio.paused) {
          audio.pause();
        }
      });

      audioRef.current.play().catch(e => {
        console.error("Audio playback error:", e);
        setIsPlaying(false);
      });
    }
  };

  return (
    <>
      <audio
        ref={audioRef}
        src={src}
        onEnded={() => setIsPlaying(false)}
        onPause={() => setIsPlaying(false)}
        onPlay={() => setIsPlaying(true)}
        preload="auto"
      />
      <button
        onClick={togglePlay}
        type="button"
        className="btn btn-ghost btn-xs"
        style={{ marginTop: '8px', padding: '6px 10px', display: 'flex', alignItems: 'center', gap: '6px', textTransform: 'uppercase', fontSize: '11px', backgroundColor: 'rgba(0,0,0,0.1)', border: '2px solid var(--border)' }}>
        <Volume2 size={14} /> {isPlaying ? "Stop Audio" : "Play Audio Summary"}
      </button>
    </>
  );
}

function ChatBox({ itemResult }) {
  const [isOpen, setIsOpen] = useState(true);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hi! I am ChestVision AI. I have analyzed your X-ray results. What would you like to know?', audio_url: null }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  React.useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg = input.trim();
    if (userMsg.toLowerCase() === 'bye') {
      setIsOpen(false);
      return;
    }

    const newMessages = [...messages, { role: 'user', content: userMsg }];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          detection: itemResult,
          question: userMsg,
          history: messages.map(m => `${m.role}: ${m.content}`).join("\\n")
        })
      });
      const data = await response.json();
      const answer = data.answer || data.response || (typeof data === 'string' ? data : JSON.stringify(data));
      setMessages([...newMessages, { role: 'assistant', content: answer, audio_url: data.audio_url }]);
    } catch {
      setMessages([...newMessages, { role: 'assistant', content: "Backend /chat endpoint is not reachable yet." }]);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) {
    return (
      <div className="chat-container">
        <button onClick={() => setIsOpen(true)} className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
          <MessageSquare size={16} /> Open AI Chat Assistant
        </button>
      </div>
    );
  }

  return (
    <div className="chat-container">
      <div className="chat-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <MessageSquare size={16} /> AI Chat Assistant
        </div>
        <button onClick={() => setIsOpen(false)} className="btn btn-ghost btn-xs" style={{ padding: '4px 8px' }}>Close</button>
      </div>
      <div className="chat-box">
        <div className="chat-messages">
          {messages.map((m, i) => (
            <div key={i} className={`chat-message ${m.role}`}>
              {m.content}
              {m.audio_url && <AudioPlayer src={m.audio_url} />}
            </div>
          ))}
          {loading && <div className="chat-message assistant">Thinking...</div>}
          <div ref={messagesEndRef} />
        </div>
        <form onSubmit={sendMessage} className="chat-input-form">
          <input
            type="text"
            className="chat-input"
            placeholder="Type your question... (type 'bye' to close)"
            value={input}
            onChange={e => setInput(e.target.value)}
          />
          <button type="submit" className="btn btn-primary" style={{ padding: '8px 12px' }} disabled={loading || !input.trim()}>
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
}

function Navbar() {
  const { pathname } = useLocation();
  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="nav-logo">
          <div className="logo-icon-sm">
            <Stethoscope size={18} />
          </div>
          <span>ChestVision AI</span>
        </Link>
        <div className="nav-links">
          <Link to="/" className={`nav-link ${pathname === "/" ? "active" : ""}`}>
            <Target size={16} />
            <span>Detector</span>
          </Link>
          <Link to="/about" className={`nav-link ${pathname === "/about" ? "active" : ""}`}>
            <Info size={16} />
            <span>About</span>
          </Link>
        </div>
      </div>
    </nav>
  );
}

function Home() {
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [showBoxes, setShowBoxes] = useState(true);
  const inputRef = useRef(null);

  const handleFiles = useCallback((selectedFiles) => {
    if (!selectedFiles || selectedFiles.length === 0) return;
    const fileArray = Array.from(selectedFiles);
    setFiles(fileArray);

    const newPreviews = fileArray.map((f) => URL.createObjectURL(f));
    setPreviews(newPreviews);
    setResult(null);
  }, []);

  const handleFileChange = (e) => handleFiles(e.target.files);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === "dragenter" || e.type === "dragover");
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.length > 0) handleFiles(e.dataTransfer.files);
  };

  const clearFiles = () => {
    setFiles([]);
    setPreviews([]);
    setResult(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (files.length === 0) return;
    setLoading(true);
    setResult(null);

    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    try {
      const response = await fetch("http://127.0.0.1:8000/batch_predict", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      setResult(data);
    } catch {
      alert("Prediction failed. Please check the backend connection.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="home-content">
      {/* Hero */}
      <section className="hero">
        <h2 className="hero-title">
          AI-Powered Chest X-Ray<br />Abnormality Detection
        </h2>
        <p className="hero-desc">
          Upload chest X-rays to detect up to 14 different abnormalities with bounding
          box localization using our YOLO11 deep learning model. Switch to batch upload to predict multiple fast.
        </p>
        <div className="hero-stats">
          <div className="stat-pill">
            <Target size={14} />
            <span>14 Classes</span>
          </div>
          <div className="stat-pill">
            <Activity size={14} />
            <span>33.6% mAP</span>
          </div>
          <div className="stat-pill">
            <Zap size={14} />
            <span>~13ms Inference</span>
          </div>
        </div>
      </section>

      <div className="main-layout">
        <div className="layout-left">
          {/* Upload card */}
          <section className="card upload-card">
            <div className="card-header">
              <FileImage size={18} />
              <span>Upload X-Ray Images</span>
            </div>

            <form onSubmit={handleSubmit}>
              <label
                className={`dropzone ${dragActive ? "dropzone-active" : ""} ${previews.length > 0 ? "dropzone-has-file" : ""}`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  ref={inputRef}
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleFileChange}
                  hidden
                />

                {!previews.length ? (
                  <div className="dropzone-content">
                    <div className="dropzone-icon-wrap">
                      <Upload size={28} />
                    </div>
                    <p className="dropzone-primary">
                      Click to upload or drag & drop multiple files
                    </p>
                    <p className="dropzone-secondary">
                      PNG, JPG, DICOM up to 10 MB per file
                    </p>
                  </div>
                ) : (
                  <div
                    className="preview-grid"
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                      gap: "12px",
                      padding: "16px",
                      width: "100%",
                    }}
                  >
                    {previews.map((preview, idx) => (
                      <div key={idx} className="preview-wrap">
                        <img
                          src={preview}
                          alt={`Preview ${idx}`}
                          className="preview-img"
                          style={{ maxHeight: "180px", width: "100%", objectFit: "cover" }}
                        />
                        <div className="preview-overlay" style={{ padding: "8px" }}>
                          <span className="preview-filename">{files[idx].name}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </label>

              <div className="action-row">
                {previews.length > 0 && (
                  <button type="button" className="btn btn-ghost" onClick={clearFiles}>
                    <Trash2 size={16} /> Remove All
                  </button>
                )}
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={files.length === 0 || loading}
                >
                  {loading ? (
                    <>
                      <Activity size={16} className="spin" /> Detecting...
                    </>
                  ) : (
                    <>
                      <Target size={16} /> Detect Abnormalities
                    </>
                  )}
                </button>
              </div>
            </form>
          </section>
        </div>

        <div className="layout-right">
          {/* Loading state */}
          {loading && (
            <section className="card loading-card">
              <div className="pulse-ring" />
              <p className="loading-title">Scanning X-rays for abnormalities</p>
              <p className="loading-sub">
                Running YOLO11 object detection in batch mode...
              </p>
            </section>
          )}

          {/* Results */}
          {result && result.results && (
            <div className="batch-results fade-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              {result.results.length > 1 && (
                <div
                  className="card-header"
                  style={{
                    marginBottom: 0,
                    justifyContent: "space-between",
                    display: "flex",
                  }}
                >
                  <span>
                    <Activity
                      size={18}
                      style={{ display: "inline", marginRight: "8px", verticalAlign: "text-bottom" }}
                    />
                    Batch Prediction Results
                  </span>
                  <span className="badge badge-sm">
                    {result.total_images} images processed in {result.total_time_seconds}s
                  </span>
                </div>
              )}

              {result.results.map((itemResult, idx) => {
                const hasDetections = itemResult.num_detections > 0;
                const previewUrl = previews[idx];

                return (
                  <section key={idx} className="card result-card">
                    <div className="card-header">
                      <FileImage size={18} />
                      <span>{itemResult.filename}</span>
                      {itemResult.inference_time_seconds && (
                        <span className="badge badge-sm">{itemResult.inference_time_seconds}s</span>
                      )}
                    </div>

                    {/* Summary banner */}
                    <div
                      className={`result-summary ${hasDetections ? "result-warning" : "result-ok"
                        }`}
                    >
                      {hasDetections ? (
                        <AlertCircle size={28} />
                      ) : (
                        <CheckCircle2 size={28} />
                      )}
                      <div>
                        <p className="summary-label">
                          {hasDetections
                            ? "Abnormalities Detected"
                            : "No Abnormalities Found"}
                        </p>
                        <p className="summary-text">
                          {hasDetections
                            ? `${itemResult.detections[0].class_name} (${(
                              itemResult.detections[0].confidence * 100
                            ).toFixed(1)}% confidence)`
                            : "No abnormalities detected"}
                        </p>
                      </div>
                      {hasDetections && (
                        <span className="det-count">{itemResult.num_detections}</span>
                      )}
                    </div>

                    {/* Image with bounding boxes */}
                    {previewUrl && hasDetections && (
                      <div className="detection-image-section">
                        <div className="det-image-header">
                          <span className="det-image-title">
                            <Eye size={15} /> Localized Findings
                          </span>
                          <button
                            className="btn btn-ghost btn-xs"
                            onClick={() => setShowBoxes(!showBoxes)}
                          >
                            {showBoxes ? "Hide Boxes" : "Show Boxes"}
                          </button>
                        </div>
                        <div className="det-image-wrap">
                          <img
                            src={previewUrl}
                            alt="Detection result"
                            className="det-result-img"
                          />
                          {showBoxes && itemResult.image_size && (
                            <BBoxOverlay
                              detections={itemResult.detections}
                              imgWidth={itemResult.image_size.width}
                              imgHeight={itemResult.image_size.height}
                            />
                          )}
                        </div>
                      </div>
                    )}

                    {/* Detection list */}
                    {hasDetections && (
                      <div className="detections-list">
                        <p className="det-list-title">Detected Abnormalities</p>
                        {itemResult.detections.map((det, i) => (
                          <DetectionCard key={i} det={det} index={i} />
                        ))}
                      </div>
                    )}

                    {/* Chatbot */}
                    <ChatBox itemResult={itemResult} />

                    <p className="disclaimer" style={{ marginTop: "18px" }}>
                      This AI analysis is for research/educational purposes only and should not
                      replace professional medical diagnosis.
                    </p>
                  </section>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <div className="app-root">
      {/* Ambient blobs */}
      <div className="blob blob-1" />
      <div className="blob blob-2" />
      <div className="blob blob-3" />

      {/* Navbar */}
      <Navbar />

      <main className="main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/about" element={<About />} />
        </Routes>
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-inner">
          <span className="footer-left">
            <Heart size={14} /> Built with YOLO11 &middot; PyTorch &middot; FastAPI
          </span>
        </div>
      </footer>
    </div>
  );
}
