
import React from "react";
import {
  Info,
  Cpu,
  Database,
  Layers,
  FileText,
  ShieldAlert,
  ExternalLink,
  ChevronRight,
  BookOpen,
  LineChart
} from "lucide-react";

export default function About() {
  return (
    <div className="about-page fade-in">
      <section className="about-hero">
        <div className="about-hero-content">
          <div className="about-badge">
            <Info size={14} />
            <span>Project Documentation</span>
          </div>
          <h1 className="about-title">ChestVision AI</h1>
          <p className="about-subtitle">
            Advancing Medical Imaging with State-of-the-Art Deep Learning
          </p>
        </div>
      </section>

      <div className="about-container">
        {/* Project Overview */}
        <section className="about-section card">
          <div className="about-section-header">
            <div className="section-icon"><BookOpen size={20} /></div>
            <h2>Project Overview</h2>
          </div>
          <div className="section-body">
            <p>
              ChestVision AI is a specialized computer vision platform designed to assist
              radiologists by automatically localizing abnormalities in chest X-rays.
              By utilizing the latest <strong>YOLO11</strong> architecture, the system
              can simultaneously detect and classify 14 distinct pathologies with
              high precision and near-instant inference speeds.
            </p>
          </div>
        </section>

        {/* Tech Stack */}
        <div className="about-grid">
          <section className="about-section card">
            <div className="about-section-header">
              <div className="section-icon"><Cpu size={20} /></div>
              <h2>Tech Stack</h2>
            </div>
            <div className="section-body">
              <ul className="tech-list">
                <li>
                  <strong>YOLO11m</strong>
                  <span>Latest Ultralytics model optimized for accuracy and speed.</span>
                </li>
                <li>
                  <strong>PyTorch</strong>
                  <span>Deep learning framework for robust training and inference.</span>
                </li>
                <li>
                  <strong>FastAPI</strong>
                  <span>Asynchronous Python backend for high-performance API serving.</span>
                </li>
                <li>
                  <strong>Vite + React</strong>
                  <span>Modern frontend stack for a sleek, responsive user experience.</span>
                </li>
              </ul>
            </div>
          </section>

          <section className="about-section card">
            <div className="about-section-header">
              <div className="section-icon"><Database size={20} /></div>
              <h2>Dataset Details</h2>
            </div>
            <div className="section-body">
              <p>
                Our model is trained on a derivation of the <strong>VinBigData Chest X-ray
                  Abnormalities Dataset</strong>, which features 15,000 images annotated
                by expert radiologists.
              </p>
              <div className="metric-pill">
                <LineChart size={14} />
                <span>mAP50: 33.6% (Benchmark)</span>
              </div>
              <p className="mt-4 text-sm opacity-70">
                Data was preprocessed with CLAHE and lung-cropping to enhance
                structural features.
              </p>
            </div>
          </section>
        </div>

        {/* How it works */}
        <section className="about-section card">
          <div className="about-section-header">
            <div className="section-icon"><Layers size={20} /></div>
            <h2>The Detection Pipeline</h2>
          </div>
          <div className="section-body">
            <div className="pipeline-steps">
              <div className="step">
                <div className="step-num">1</div>
                <div className="step-content">
                  <h3>Preprocessing</h3>
                  <p>Images are resized to 640x640 and normalized to match the YOLO11 input requirements.</p>
                </div>
              </div>
              <div className="step">
                <div className="step-num">2</div>
                <div className="step-content">
                  <h3>Feature Extraction</h3>
                  <p>The CSPDarknet backbone extracts multiscale spatial features from the X-ray structure.</p>
                </div>
              </div>
              <div className="step">
                <div className="step-num">3</div>
                <div className="step-content">
                  <h3>BBox Regression</h3>
                  <p>The model predicts bounding box coordinates and objectness scores across 14 classes.</p>
                </div>
              </div>
              <div className="step">
                <div className="step-num">4</div>
                <div className="step-content">
                  <h3>Non-Max Suppression</h3>
                  <p>Overlapping detections are filtered to ensure only the highest confidence results remain.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Usage Guide */}
        <section className="about-section card">
          <div className="about-section-header">
            <div className="section-icon"><FileText size={20} /></div>
            <h2>User Guide</h2>
          </div>
          <div className="section-body usage-guide">
            <div className="guide-item">
              <ChevronRight size={18} />
              <p><strong>Upload:</strong> Drop an X-ray (PNG or JPG) into the detector tool.</p>
            </div>
            <div className="guide-item">
              <ChevronRight size={18} />
              <p><strong>Analyze:</strong> Click "Detect Abnormalities" to run the AI scan.</p>
            </div>
            <div className="guide-item">
              <ChevronRight size={18} />
              <p><strong>Review:</strong> View the summary banner and the pinpointed boxes on the image.</p>
            </div>
          </div>
        </section>

        {/* Disclaimer */}
        <section className="disclaimer-large">
          <div className="disclaimer-header">
            <ShieldAlert size={24} />
            <h2>Medical & Research Disclaimer</h2>
          </div>
          <p>
            ChestVision AI is strictly for **research and educational purposes**.
            It is not intended for clinical use or to replace the professional judgement
            of a qualified radiologist. This tool helps illustrate deep learning capabilities
            in medical imaging but should never be used as the sole basis for surgical
            or clinical decisions.
          </p>
        </section>

        <footer className="about-footer">
          <p>Developed with ❤️ for Academic Research</p>
        </footer>
      </div>
    </div>
  );
}
