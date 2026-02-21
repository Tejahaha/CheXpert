import os
import uuid
import numpy as np
import subprocess
import requests
from fastapi import APIRouter
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

router = APIRouter()

medical_knowledge = {
    "Atelectasis": """Atelectasis refers to partial or complete collapse of a portion of the lung. 
It occurs when air cannot properly reach the alveoli, often due to airway blockage, mucus plugs, or external compression. 
On chest X-ray, it may appear as an area of increased density with reduced lung volume. 
It can develop after surgery, infection, or prolonged immobility. 
Symptoms may include shortness of breath, shallow breathing, or decreased oxygen levels.""",

    "Cardiomegaly": """Cardiomegaly means enlargement of the heart. 
On a chest X-ray, it is identified when the heart silhouette appears larger than normal relative to the chest cavity. 
It may be associated with hypertension, heart failure, or cardiomyopathy. 
The enlargement may indicate that the heart is working harder than usual. 
Symptoms can include fatigue, swelling of the legs, and shortness of breath.""",

    "Consolidation": """Consolidation occurs when air in the alveoli is replaced by fluid, pus, blood, or inflammatory cells. 
It is most commonly seen in infections such as pneumonia. 
On imaging, it appears as a dense white region in the lung field. 
Consolidation reduces normal oxygen exchange in the affected area. 
Patients may experience fever, productive cough, and chest pain while breathing.""",

    "Edema": """Pulmonary edema is the accumulation of fluid inside lung tissue and air spaces. 
It is often related to heart failure but may also result from infection or injury. 
On chest X-ray, it can appear as diffuse hazy or cloudy opacities. 
The fluid buildup interferes with oxygen transfer into the bloodstream. 
Symptoms include difficulty breathing, especially when lying down.""",

    "Pleural Effusion": """Pleural effusion is the buildup of fluid between the layers of tissue lining the lungs and chest wall. 
This fluid accumulation can compress the lung and limit expansion. 
On imaging, it may cause blunting of the costophrenic angle. 
It can result from infection, heart failure, or malignancy. 
Patients may report chest heaviness and shortness of breath.""",

    "Pneumothorax": """Pneumothorax occurs when air enters the space between the lung and chest wall. 
This causes partial or complete collapse of the affected lung. 
On chest X-ray, it appears as absence of lung markings beyond the collapsed area. 
It may occur spontaneously or due to trauma. 
Symptoms often include sudden sharp chest pain and shortness of breath.""",

    "Lung Opacity": """Lung opacity is a general term describing any area that appears whiter than normal lung tissue on a chest X-ray. 
It does not specify a diagnosis but indicates an abnormality. 
Possible causes include infection, inflammation, fluid, scarring, or tumor. 
Further clinical correlation is required to determine the underlying cause. 
Symptoms vary depending on the specific condition.""",

    "Pulmonary Fibrosis": """Pulmonary fibrosis is a chronic condition characterized by progressive scarring of lung tissue. 
The scarring thickens the lung walls and reduces flexibility. 
This limits the lungs' ability to transfer oxygen into the bloodstream. 
On imaging, it may appear as reticular or interstitial patterns. 
Patients typically experience gradually worsening shortness of breath.""",

    "Infiltration": """Infiltration refers to abnormal accumulation of inflammatory cells, fluid, or substances within lung tissue. 
It is commonly associated with infections such as pneumonia. 
On chest X-ray, it may appear as patchy or diffuse opacities. 
The finding suggests inflammation but does not confirm a specific cause. 
Clinical evaluation is necessary to determine the underlying condition.""",

    "Enlarged Mediastinum": """An enlarged mediastinum refers to widening of the central compartment of the chest. 
This area contains the heart, major blood vessels, trachea, and lymph nodes. 
Widening may be caused by masses, lymph node enlargement, bleeding, or vascular abnormalities. 
It may require further imaging such as CT scan for clarification. 
Symptoms depend on the underlying cause.""",

    "Nodule": """A lung nodule is a small, round growth in the lung usually less than 3 centimeters in size. 
It may be detected incidentally on chest imaging. 
Nodules can be benign, such as from prior infection, or malignant. 
The size, shape, and growth over time help determine risk. 
Further imaging follow-up may be required.""",

    "Mass": """A lung mass is a larger abnormal growth in lung tissue, typically greater than 3 centimeters. 
It may represent malignancy, severe infection, or inflammatory disease. 
On chest X-ray, it appears as a distinct dense region. 
Additional imaging or biopsy may be needed for diagnosis. 
Symptoms may include cough, chest pain, or weight loss.""",

    "Pleural Thickening": """Pleural thickening refers to fibrosis or scarring of the pleural lining surrounding the lungs. 
It may occur after infection, inflammation, or asbestos exposure. 
On imaging, it appears as irregular thickened areas along the lung border. 
Severe thickening may restrict lung expansion. 
Symptoms may include mild breathing discomfort.""",

    "Calcification": """Calcification refers to calcium deposits within lung tissue or lymph nodes. 
It often indicates prior healed infection or inflammation. 
On chest X-ray, calcified areas appear denser and well-defined. 
In many cases, calcification is benign. 
Clinical context determines whether further evaluation is needed.""",

    "Rib Fracture": """A rib fracture is a break in one of the rib bones, commonly caused by trauma. 
On chest X-ray, it may appear as discontinuity or irregularity in the rib structure. 
Pain often worsens with deep breathing or movement. 
Most rib fractures heal with supportive care. 
Severe cases may affect breathing mechanics.""",

    "Aortic Enlargement": """Aortic enlargement refers to widening or dilation of the aorta, the main artery carrying blood from the heart. 
It may be associated with hypertension, aging, connective tissue disorders, or aneurysm formation. 
On chest X-ray, it can appear as widening of the mediastinum or prominence of the aortic knob. 
Further imaging such as CT scan may be required for confirmation. 
The clinical significance depends on size and progression.""",

    "No Finding": """No visible abnormality was detected on the chest X-ray. 
This suggests the image does not show obvious structural issues. 
However, imaging findings should always be interpreted alongside clinical symptoms. 
Some conditions may not be visible on X-ray alone. 
Medical evaluation is recommended if symptoms persist."""
}

print("Loading embedding model...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

knowledge_list = list(medical_knowledge.values())
knowledge_embeddings = embed_model.encode(knowledge_list)

def retrieve_fallback(query, top_k=1):
    query_embedding = embed_model.encode([query])[0]
    similarities = np.dot(knowledge_embeddings, query_embedding)
    top_indices = np.argsort(similarities)[-top_k:]
    return [knowledge_list[i] for i in top_indices]

def ask_llama(prompt):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3:8b",
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        return response.json()["response"]
    except Exception as e:
        print(f"Error connecting to Ollama: {e}")
        return "I'm currently unable to connect to my AI brain (Ollama). Please ensure the service is running locally!"

def summarize_to_points(text):
    prompt = f"""
Summarize the following medical explanation into exactly 3 to 5 short, clear bullet points.
Keep each point under 20 words.
Do not repeat sentences.
Keep it simple, empathetic, and patient-friendly.

Explanation:
{text}
"""
    return ask_llama(prompt)

def generate_voice_file(text):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    piper_path = os.path.join(base_dir, "piper", "piper.exe")
    model_path = os.path.join(base_dir, "piper", "voices", "en_US-hfc_female-medium.onnx")
    unique_id = uuid.uuid4().hex
    output_filename = f"voice_{unique_id}.wav"
    
    os.makedirs("output", exist_ok=True)
    output_file = os.path.join("output", output_filename)

    if not os.path.exists(piper_path):
        print(f"Piper missing at {piper_path}, skipping text-to-speech.")
        return None

    command = [
        piper_path,
        "--model", model_path,
        "--output_file", output_file
    ]

    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, text=True)
        process.communicate(text)
        return output_filename
    except Exception as e:
        print(f"Error generating voice: {e}")
        return None

class ChatRequest(BaseModel):
    detection: dict
    question: str
    history: str = ""

@router.post("/chat")
def process_chat(request: ChatRequest):
    findings = []
    context_blocks = []

    detections = request.detection.get("detections", [])
    for det in detections:
        finding = det.get("class_name", "Unknown")
        confidence = det.get("confidence", 0.0)

        findings.append(f"{finding} ({confidence*100:.1f}%)")

        if finding in medical_knowledge:
            context_blocks.append(medical_knowledge[finding])
        else:
            fallback = retrieve_fallback(finding)
            context_blocks.extend(fallback)

    context = "\n".join(context_blocks)
    conversation_history = request.history + f"\nUser: {request.question}"

    prompt = f"""
You are ChestVision AI, a friendly, empathetic, and highly knowledgeable medical assistant.
You are having a warm, 1-on-1 text conversation with someone asking about their Chest X-ray.

Chest X-ray Findings:
{", ".join(findings) if findings else "No visible abnormalities."}

Relevant Medical Context:
{context}

Conversation so far:
{conversation_history}

Instructions:
- Speak in a warm, reassuring, and human-like tone, demonstrating care for the patient.
- Explain the findings and their confidence levels clearly in simple, natural language.
- DO NOT diagnose the patient with absolute certainty—always warmly remind them that you are an AI assistant.
- Encourage them to consult a human healthcare professional or radiologist for official advice.
- Keep your response conversational and relatively concise. DO NOT write long essays.

ChestVision AI:
"""

    answer = ask_llama(prompt)

    if "unable to connect" in answer:
        return {
            "answer": answer,
            "audio_url": None
        }

    summary = summarize_to_points(answer)
    audio_file = generate_voice_file(summary)

    audio_url = f"http://127.0.0.1:8000/output/{audio_file}" if audio_file else None

    return {
        "answer": answer,
        "audio_url": audio_url
    }