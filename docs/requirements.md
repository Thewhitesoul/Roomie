# Roomie Requirements and Functional Specification

## 1 Purpose

This document defines the initial functional and nonfunctional requirements for Roomie. It is intended to guide design, implementation, and testing and will be revised as the project develops.

## 2 Overall Description

Roomie is a roommate and room-finding web application. A user creates an account and profile, enters lifestyle information, interests, housing needs, and roommate preferences, and views relevant people or rooms. Users who already have a room may create a listing in the fully realized system. Roomie helps users discover possible connections but does not make housing decisions for them or guarantee compatibility, profile accuracy, or personal safety.

## 3 Requirements Sources

The requirements were derived from:

- The CM333 group project instructions
- The Roomie problem statement
- Identified stakeholders
- Three user personas
- Prioritized user stories and acceptance criteria
- Team discussions about the MVP and planned technology
- Research and guidance concerning web accessibility, authentication, database use, and application security

## 4 Users and Personas

### 4.1 First-Year College Student Looking for a Roommate

This user wants a simple process for comparing study habits, cleanliness, sleep schedules, interests, and other lifestyle preferences before contacting someone.

### 4.2 Student Moving to a New Area

This user may need both a room and a compatible roommate. The interface should provide clear labels, readable information, responsive pages, and support for phone-sized screens.

### 4.3 Student With an Available Room

This user wants to describe an available room, explain the living arrangement, review potential roommates, and contact interested users. Detailed room-listing functionality is part of the full system but is outside the semester MVP.

## 5 Full System and MVP Scope

### 5.1 Full System

The full system may include registration, profiles, preferences, roommate matching, room listings, saved profiles and listings, mutual matches, messaging, notifications, reporting, and basic verification features.

### 5.2 Semester MVP

The MVP includes:

- User registration, login, and logout
- User profile creation and editing
- Lifestyle, interest, and roommate-preference entry
- Finding or filtering possible roommate matches
- Viewing potential roommate profiles
- Showing, changing, or removing interest in another profile

The MVP excludes detailed room listings, advanced housing searches, real-time messaging, notifications, advanced compatibility scoring, identity verification, background checks, payments, lease services, and property management.

## 6 Major User-Facing Features

| Feature | Description | MVP |
| --- | --- | --- |
| Account access | Register, log in, and log out. | Yes |
| Roommate profile | Create and edit personal, lifestyle, and housing information. | Yes |
| Preferences | Enter the characteristics wanted in a potential roommate. | Yes |
| Match discovery | Find or filter possible roommates using selected preferences. | Yes |
| Profile viewing | View relevant profile details without seeing private login information. | Yes |
| Interest | Show, change, or remove interest in another profile. | Yes |
| Room listings | Post and search rooms by location, price, and availability. | No |
| Messaging | Allow interested or mutually matched users to communicate. | No |
| Reporting | Report suspicious profiles or inappropriate content. | No |

## 7 Functional Requirements

| ID | Requirement | MVP |
| --- | --- | --- |
| FR-01 | The system shall allow a new user to create an account using all required registration information. | Yes |
| FR-02 | The system shall allow a registered user to log in and log out. | Yes |
| FR-03 | The system shall allow an authenticated user to create and edit a roommate profile. | Yes |
| FR-04 | A profile shall store interests, lifestyle information, housing needs, and roommate preferences. | Yes |
| FR-05 | The system shall reject a profile submission when a required field is empty and display a clear error. | Yes |
| FR-06 | The system shall allow a user to find or filter potential roommates using selected preferences. | Yes |
| FR-07 | The system shall display relevant roommate-profile information without displaying private login data. | Yes |
| FR-08 | The system shall allow a user to indicate interest in another user. | Yes |
| FR-09 | The system shall allow a user to remove or change a previously recorded interest. | Yes |
| FR-10 | The system shall prevent a user from matching with or showing interest in their own profile. | Yes |
| FR-11 | The system shall prevent unauthenticated users from opening protected profile and matching pages. | Yes |
| FR-12 | The full system shall allow users to create and view room listings containing location, price, and availability. | No |
| FR-13 | The full system shall allow eligible users to communicate within the application. | No |
| FR-14 | The full system shall allow users to report suspicious profiles or inappropriate content. | No |

## 8 User Interface Requirements

Roomie will require:

- A registration page
- A login page
- A profile creation and editing page
- A roommate-preference form
- A match-results or swiping page
- A potential-roommate profile page
- Controls for showing, changing, or removing interest
- Clear navigation and a logout control
- Validation messages and status feedback

The interface shall meet these requirements:

- The interface shall remain usable at viewport widths of 360 pixels and 1280 pixels.
- Required form fields shall have visible labels.
- Registration, profile, preference, and matching functions shall be usable with a keyboard.
- Validation messages shall identify the field or action that needs correction.
- Pages shall provide visible feedback after a user submits a form.

### 8.1 Interfaces by Persona

| Persona or User | Required Interfaces and Design Needs |
| --- | --- |
| All users | Registration, login, logout, navigation, validation messages, and status feedback. |
| Roommate seeker | Profile form, preference form, match results, profile details, and interest controls. |
| User moving to a new area | Readable room and profile information, responsive pages, and clear search or filter controls. |
| User with an available room | Room-listing form and listing-management page in the full system. |

## 9 Platform and External Interface Requirements

- Roomie will be implemented as a browser-based web application.
- The planned front end uses HTML, CSS, and JavaScript.
- The planned back end uses Python and Flask.
- Structured application data will be stored in SQLite using SQL.
- The development team will use GitHub for source control.
- The application shall support the current versions of Chrome, Firefox, Edge, and Safari used during team testing.
- Development shall be possible on macOS and Windows using the documented setup process.
- No special hardware is required beyond a computer or phone capable of running a modern browser.
- Users need an internet or local-network connection to the application server.
- The MVP does not require payment, mapping, background-check, or identity-verification services.

## 10 Performance, Reliability, and Security Requirements

### 10.1 Performance

- During team testing, at least 95 percent of normal page requests shall complete within three seconds in the supported development environment.
- A match search using 500 seeded profiles shall return results within two seconds in the supported development environment.
- The interface shall provide feedback after a user submits a form.

### 10.2 Reliability

- Invalid or incomplete required data shall be rejected with a clear error message.
- A failed account or profile write shall not leave a partially created record.
- All critical automated tests shall pass before the MVP demonstration.
- The team shall record discovered defects and failed tests.

### 10.3 Security and Privacy

- Passwords shall be stored as salted password hashes and never as plain text.
- Protected pages shall require an authenticated session.
- Database operations shall use parameterized queries.
- The application shall validate and limit user-controlled input.
- Secret keys, virtual environments, and local database files shall not be committed to GitHub.
- Profiles and match results shall not expose private login data.
- Login failure messages shall not reveal whether a particular account exists.
- Users shall control the profile and preference information they enter into the system.

## 11 Project Boundary

### Roomie IS

- A roommate and room-finding application
- A platform for creating roommate profiles
- A way to share relevant lifestyle and roommate preferences
- A tool for finding potential roommates and rooms
- A tool that helps interested users connect and make their own decisions

### Roomie IS NOT

- A landlord, rental agency, or property-management system
- A lease or legal-contract service
- A rent or deposit payment platform
- A background-check service in the MVP
- A guarantee that profiles are accurate
- A guarantee that users will be compatible or safe

## 12 Initial Data and Software Elements

### 12.1 Data Objects

| Element | Purpose |
| --- | --- |
| User | Stores account identity and account status. |
| Login Credential | Stores the password hash and authentication-related data. |
| Roommate Profile | Stores information displayed to possible roommates. |
| Preference | Stores lifestyle and roommate preferences used for filtering. |
| Housing Need | Stores the user's room, location, and housing needs. |
| Interest | Records one user's interest in another profile. |
| Match Result | Represents a possible roommate returned by filtering. |
| Room Listing | Stores location, price, and availability in the full system. |
| Message | Stores communication between eligible users in the full system. |

### 12.2 Planned Services and Functions

- Account registration
- Authentication and session management
- Profile management
- Preference validation
- Match filtering
- Profile display
- Interest management
- Database access
- Input validation
- Testing and error handling

## 13 Constraints and Assumptions

- The project is a semester MVP with limited development time.
- The team will prioritize the shortest complete roommate-finding workflow.
- Users are responsible for evaluating potential roommates and housing arrangements.
- Features outside the MVP may appear in design documents without being implemented.
- Requirements may change after instructor feedback, implementation findings, or testing.

## 14 References

1. Flask Documentation: https://flask.palletsprojects.com/
2. Python SQLite3 Documentation: https://docs.python.org/3/library/sqlite3.html
3. OWASP Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
4. MDN Web Docs: https://developer.mozilla.org/en-US/docs/Web/
5. Web Content Accessibility Guidelines 2.2: https://www.w3.org/TR/WCAG22/
