
# 🧿 DemonSeller

DemonSeller is an AI-powered property selling platform designed specifically for agent deller. The system enables agent deller to upload **videos**, **images**, and **text files** describing properties (primarily flats), and uses a team of specialized AI agents to extract insights, store structured data, and retrieve relevant listings based on dynamic requirements.

---

## 🚀 Features

- 📤 Upload Support for:
  - Text Descriptions
  - Property Images
  - Walkthrough Videos

- 🧠 AI Agentic Pipeline:
  - **Image Agent**: Processes and understands property images.
  - **Video Agent**: Extracts keyframes and context from walkthrough videos.
  - **Text Agent**: Extracts structured information from broker descriptions.
  - **Search Agent**: Matches buyer requirements with available properties.

- 🔍 Intelligent Property Matching:
  - Retrieve best-fit properties from database.
  - AI-powered filtering based on uploaded requirements.

---

## 🧠 AI Agent Teamwork

Each AI agent is responsible for a specialized task. The agents collaborate to process, understand, and recommend property listings with high precision.

```mermaid
graph TD
    Upload[Broker Uploads Media] --> ImageAgent
    Upload --> VideoAgent
    Upload --> TextAgent
    ImageAgent -->|Processed Image Data| AI_Team
    VideoAgent -->|Processed Video Data| AI_Team
    TextAgent -->|Extracted Textual Info| AI_Team
    AI_Team[AI Team DB Handler] --> DB[(Database)]
    BuyerQuery[Buyer Requirement Input] --> SearchAgent
    SearchAgent --> DB
    DB --> Result[Relevant Property Recommendations]
````

---

## 🧱 System Architecture

```mermaid
flowchart TD
    Broker -->|Uploads Media| MediaHandler
    MediaHandler -->|Send to ImageAgent| ImageAgent
    MediaHandler -->|Send to VideoAgent| VideoAgent
    MediaHandler -->|Send to TextAgent| TextAgent
    ImageAgent -->|Structured Image Metadata| AgentHub
    VideoAgent -->|Video Insights & Frames| AgentHub
    TextAgent -->|Key Info from Text| AgentHub
    AgentHub -->|Save All Media Info| DB[(Vector/Relational DB)]
    ClientRequest[Broker/Client Requirement] --> SearchAgent
    SearchAgent -->|Fetch from DB| DB
    DB -->|Matching Flats| Response[Filtered Properties Returned]
```

---

## 📦 Tech Stack

* **Backend**: Python / Node.js
* **Database**:  Vector DB (e.g., Pinecone or FAISS)
* **AI Models**:
* **Frameworks**: FastAPI / StreamlIT 
* **Agents**: Multi-agent collaboration orchestrated via Agno 

---

## 🏗️ Folder Structure (Planned)

```
DemonSeller/
├── agents/
│   ├── image_agent/
│   ├── video_agent/
│   ├── text_agent/
│   └── search_agent/
├── database/
│   └── models/
├── media/
├── api/
│   ├── routes/
│   └── middleware/
├── utils/
├── tests/
└── README.md
```

---

## 🤖 AI Agents Description

| Agent          | Task Responsibility                                    |
| -------------- | ------------------------------------------------------ |
| 🖼️ ImageAgent | Handles property image classification & tagging        |
| 📹 VideoAgent  | Extracts room types, quality metrics from walkthroughs |
| 📄 TextAgent   | Extracts structured features from text descriptions    |
| 🔎 SearchAgent | Matches broker/buyer requirements with DB entries      |

These agents work together in a **multi-agent team**, collaborating on media understanding, data transformation, and intelligent search.

---

## 📈 Future Enhancements

* 🧩 Integration with LLM for conversational querying.
* 🌐 Web dashboard for agent deller to visualize properties.
* 📱 Mobile app with camera upload and live feedback.
* 🕵️‍♂️ Explainable AI reports per property.

---

## 🏁 Getting Started

```bash
# Clone the repository
git clone https://github.com/jayanth119/DemonSeller
cd DemonSeller

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run  main.py
```

---

## 📬 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

## ⚖️ License

[MIT](LICENSE)

---

## 👨‍💻 Author

**Jayanth Chukka**


---

