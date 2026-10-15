# Roomie Database Design

## 1. Introduction
This document describes the initial database design for Roomie, a web application that helps college students find compatible roommates. The database will store user accounts, profiles, lifestyle preferences, and roommate interest requests. Room listings are included as a future feature.

## 2. Planned Database Tables

### 2.1 User
Purpose: Stores account information for each registered user.

Fields:
- user_id: Primary key. Unique identifier for each user.
- username: Required and unique username.
- email: Required and unique email address.
- password_hash: Required. Stores the hashed password, never the original password.
- created_at: Required. Records when the account was created.

Primary Key: user_id
Foreign Keys: None
Required Fields: All fields.

### 2.2 Profile
Purpose: Stores personal and housing information that users share to help find roommates.

Fields:
- profile_id: Primary key. Unique identifier for each profile.
- user_id: Required foreign key referencing User.user_id. Must be unique.
- name: Required. User's display name.
- age: Required. User's age.
- bio: Optional. Short introduction about the user.
- location: Required. User's preferred or current location.
- housing_status: Required. Indicates whether the user needs housing or already has housing.

Primary Key: profile_id
Foreign Key: user_id references User.user_id
Required Fields: profile_id, user_id, name, age, location, housing_status.

### 2.3 Preference
Purpose: Stores the lifestyle habits and roommate preferences used for comparing potential roommates.

Fields:
- preference_id: Primary key. Unique identifier for each preference record.
- user_id: Required foreign key referencing User.user_id. Must be unique.
- cleanliness: Optional. User's cleanliness preference.
- sleep_schedule: Optional. User's preferred sleep schedule.
- study_habits: Optional. User's study habits.
- smoking_preference: Optional. User's smoking preference.
- pet_preference: Optional. User's pet preference.
- budget: Optional. User's housing budget.

Primary Key: preference_id
Foreign Key: user_id references User.user_id
Required Fields: preference_id and user_id. Preference values can be completed or updated by the user.

### 2.4 Interest
Purpose: Records when one user expresses interest in another potential roommate.

Fields:
- interest_id: Primary key. Unique identifier for each interest request.
- sender_user_id: Required foreign key referencing User.user_id. Identifies the sender.
- receiver_user_id: Required foreign key referencing User.user_id. Identifies the receiver.
- status: Required. Tracks the state of the interest request, such as pending, accepted, or declined.
- created_at: Required. Records when the request was created.

Primary Key: interest_id
Foreign Keys:
- sender_user_id references User.user_id
- receiver_user_id references User.user_id

Required Fields: All fields.

Rule: sender_user_id and receiver_user_id cannot be the same. A user cannot send an interest request to themselves.

### 2.5 RoomListing (Full System / Future Scope)
Purpose: Stores room listings created by users who have available housing. This is planned for the full Roomie system and is not necessarily part of the MVP.

Fields:
- listing_id: Primary key. Unique identifier for each listing.
- owner_user_id: Required foreign key referencing User.user_id.
- location: Required. Location of the available room.
- monthly_price: Required. Monthly housing cost.
- availability: Required. Indicates whether the room is available.
- description: Optional. Additional information about the room.

Primary Key: listing_id
Foreign Key: owner_user_id references User.user_id
Required Fields: listing_id, owner_user_id, location, monthly_price, availability.

## 3. Database Relationships

- User and Profile: One-to-one. Each user has one profile, and each profile belongs to one user. Profile.user_id is unique.
- User and Preference: One-to-one. Each user has one preference record, and each preference record belongs to one user. Preference.user_id is unique.
- User and Interest: One-to-many in each role. A user may send multiple interest requests and receive multiple interest requests. Each Interest connects one sender User to one receiver User.
- User and RoomListing: One-to-many. A user may own multiple room listings, but each listing belongs to one user.

## 4. Database Rules

1. Every table has a primary key that uniquely identifies its records.
2. Foreign keys connect related records and help maintain data consistency.
3. Usernames and email addresses must be unique.
4. Passwords must be stored only as secure password hashes, never as plain text.
5. Each User can have only one Profile and one Preference record.
6. A user cannot send an interest request to themselves.
7. Interest requests must reference existing sender and receiver users.
8. Every RoomListing must belong to an existing User.
9. RoomListing is included for the full system or future development, not necessarily the MVP.

## 5. MVP and Future Scope

The initial Roomie database design focuses on user accounts, profiles, lifestyle preferences, and roommate interest requests. These support the main roommate discovery features.

RoomListing is included in the design to show how housing listings could be supported in the complete system. It may be implemented after the MVP depending on the team's priorities.

## 6. Future Refinements

This is an initial database design. The team may refine field requirements, data types, constraints, and relationships during implementation and testing. Any changes should be discussed with the team to keep the database design consistent with the Roomie requirements.
