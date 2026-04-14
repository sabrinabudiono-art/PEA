# ⚡ PEA — Personal Energy Assistant

An AI-powered web application that helps you understand, track, and reduce your household energy consumption. Upload energy bills, chat with an intelligent assistant, manage appliances, and monitor meter readings — all in one place.

---

## ✨ Features

### 📄 Smart PDF Upload
Upload energy bills or contracts as PDF. The AI automatically extracts key data like provider name, consumption, costs, and contract terms — no manual entry needed.

### 💬 AI Energy Chat
Chat with a context-aware AI assistant that knows your energy data. Ask about your usage patterns, get personalized saving tips, or have your bills explained. Includes a **FAQ panel** with categorized frequently asked questions for quick access.

### 🔌 Appliance Tracker
Keep an inventory of your household appliances and their estimated monthly energy consumption. Includes an **AI Consumption Estimator** — describe any appliance and get an instant kWh/month estimate.

### 📊 Meter Readings
Log meter readings over time to track your consumption trends. Add, edit, and delete readings with a clean interface.

---

## 🛠️ Tech Stack

| Layer       | Technology                                                  |
|-------------|-------------------------------------------------------------|
| **Backend** | Python · Flask · Flask-SQLAlchemy                           |
| **Database**| SQLite (configurable via `DATABASE_URL`)                    |
| **AI**      | OpenAI GPT-4.1-mini                                        |
| **PDF**     | PyMuPDF4LLM (PDF → Markdown extraction)                    |
| **Frontend**| Vanilla HTML · CSS · JavaScript (single-page, no framework)|

---

## 📁 Project Structure

```
PEA/
├── app.py                 # Flask application & API routes
├── models.py              # SQLAlchemy database models
├── pdf_processor.py       # PDF to Markdown text extraction
├── pdf_extractor_ai.py    # AI-powered data extraction from PDFs
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (API keys, DB URL)
├── templates/
│   └── index.html         # Single-page frontend (HTML + JS)
├── static/
│   └── style.css          # Dark theme stylesheet
└── uploads/               # Uploaded PDF files (auto-created)
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- An [OpenAI API key](https://platform.openai.com/api-keys)

### 1. Clone the repository
```bash
git clone https://github.com/your-username/PEA.git
cd PEA
```

### 2. Create a virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file in the project root:
```env
OPENAI_API_KEY=your-openai-api-key-here
DATABASE_URL=sqlite:///pea.db
```

### 5. Run the application
```bash
python app.py
```

The app will be available at **http://localhost:5000**.

---

## 🔗 API Endpoints

### Documents
| Method   | Endpoint                       | Description                   |
|----------|--------------------------------|-------------------------------|
| `POST`   | `/api/upload`                  | Upload & analyze a PDF        |
| `GET`    | `/api/reports`                 | List all energy reports       |
| `DELETE` | `/api/reports/<id>`            | Delete an energy report       |
| `GET`    | `/api/contracts`               | List all energy contracts     |
| `DELETE` | `/api/contracts/<id>`          | Delete an energy contract     |

### Chat
| Method   | Endpoint                       | Description                   |
|----------|--------------------------------|-------------------------------|
| `POST`   | `/api/chat`                    | Send a message to the AI      |
| `DELETE` | `/api/chatbot/clear`           | Clear chat history            |

### Appliances
| Method   | Endpoint                       | Description                   |
|----------|--------------------------------|-------------------------------|
| `GET`    | `/api/appliances`              | List all appliances           |
| `POST`   | `/api/appliances`              | Add a new appliance           |
| `PUT`    | `/api/appliances/<id>`         | Update an appliance           |
| `DELETE` | `/api/appliances/<id>`         | Delete an appliance           |
| `POST`   | `/api/appliances/chat`         | AI consumption estimator      |

### Meter Readings
| Method   | Endpoint                       | Description                   |
|----------|--------------------------------|-------------------------------|
| `GET`    | `/api/meter-readings`          | List all meter readings       |
| `POST`   | `/api/meter-readings`          | Add a new reading             |
| `PUT`    | `/api/meter-readings/<id>`     | Update a reading              |
| `DELETE` | `/api/meter-readings/<id>`     | Delete a reading              |

---

## 🗄️ Database Models

| Model              | Description                                      |
|--------------------|--------------------------------------------------|
| `User`             | User accounts (username, password hash)          |
| `EnergyReport`     | Extracted data from energy bills/invoices         |
| `EnergyContract`   | Extracted data from energy contracts              |
| `Appliance`        | Tracked household appliances & consumption        |
| `MeterReadings`    | Historical meter reading entries                  |
| `Chatbot`          | Chat message history (user & assistant messages)  |

---

## 🎨 Design

- **Dark theme** with green accent colors
- **Glassmorphism** card design with backdrop blur
- **Responsive** layout — works on desktop and mobile
- **Micro-animations** for smooth interactions
- **Markdown rendering** in chat responses (bold, lists, code blocks, headings)

---

## 📝 License

This project is for personal/educational use.

---

> Built with 💚 and AI — my very first AI-powered web project!
