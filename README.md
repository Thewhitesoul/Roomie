# Roomie

Roomie is a CM333 Software Engineering group project that helps college students find compatible roommates. Users create profiles, enter lifestyle information and roommate preferences, view possible matches, and show interest in connecting.

## Problem

Finding a roommate is difficult when people do not have an organized way to compare habits, interests, housing needs, and preferences. Roomie is intended to make that process clearer while reminding users that they remain responsible for their own housing and safety decisions.

## Full System Vision

A fully developed version of Roomie could support:

- Account registration and login
- Roommate profiles and lifestyle preferences
- Potential roommate matching and filtering
- Room listings with price, location, and availability
- Saved profiles and listings
- Communication between interested users
- Notifications, reporting, and basic verification features

## Semester MVP

The semester MVP focuses on the shortest complete roommate-finding process:

1. Register and log in.
2. Create a roommate profile.
3. Enter interests, lifestyle information, and roommate preferences.
4. Find or filter possible roommate matches.
5. View another user's profile.
6. Show interest in connecting.

Detailed housing searches, real-time messaging, payments, background checks, advanced compatibility scoring, and lease management are outside the MVP.

## Planned Technology

- Front end: HTML, CSS, and JavaScript
- Back end: Python and Flask
- Database: SQLite and SQL
- Testing: pytest and manual browser testing
- Project tools: GitHub, Trello, GroupMe, and Google Drive

## Repository Structure

```text
Roomie/
├── docs/
│   ├── database-design.md
│   └── requirements.md
├── src/
│   └── README.md
├── tests/
│   └── README.md
├── .gitignore
├── README.md
└── requirements.txt
```

Application code will be added under `src/`, and automated tests will be added under `tests/`.

## Getting Started

The project is currently in the requirements, design, and initial implementation stage.

```bash
git clone https://github.com/Thewhitesoul/Roomie.git
cd Roomie
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Windows users can activate the virtual environment with:

```powershell
venv\Scripts\activate
```

## Team Workflow

- Keep `main` in a usable state.
- Create a separate branch for each feature or major task.
- Use descriptive commit messages.
- Review changes before merging them into `main`.
- Do not commit passwords, secret keys, virtual environments, or local database files.

## Team

- Stuti — Project Manager, Documentation, and Database
- Swikar — UI/UX and Frontend
- Arpan — Backend
- Rajju — Testing/QA and Integration
