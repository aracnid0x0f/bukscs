I've supplied `clinic/models.py`, `clinic/views.py`, `users/models.py` and `user/views.py`. Read them and derive context.

We will be working on the receptionist side of the system
Based on the files i provided:

1. Check for any mistakes in the code, mention and fix them

2. I need views, templates and urls for the the receptionist_dashboard.html
Here is the work of the Receptionist:

- Onboard a student in to the clinic system, basically registering them.
- Checking in a visiting patient (whom is a student) using either their Registration number or the Clinic Code
- Checking in the patient triggers the creation of a Ticket (models is Encounter from `clinic/models.py`), which is pushed into the queue for a Nurse to comsume.
    - Said Ticket will have a status "RECEPTION", to enable the Nurse to consume tickets only ment for them

3. All activities of the receptionist remains in the receptionist dashboard, never should they ever leave of call a url out side their scope, we will implement auth later.

> Take inspiration from the `receptionist_dashboard`.png file i provided, but add anything you think will be needed.
> ! Make sure the template page is fully funtional and dynamic. 

# Extra
- We are using lucid icons for the icons and `DESING.md` specifies the color pallete, but you can mke corrections where you think wil

# Receptionist dashboard

now lets redo the receptionist dashboard pages, we will be following  the neomorphism style throughout the entire project from here.

The core of this application is a Ticketing system (uses a message queue), which is created by the Receptionist, then forwarded to the Nurse, then to Doctor, then to either Lab Scientist then back to Doctor then to Pharmacist, or directly to the Pharmacist.

Here is what i want:

- a Side Navbar with the linking to the following pages:

    - Search Student page (patient), with the following functions:

        - search a student by clinic code, name or reg number. If student doesnt exist, suggest to register student

        - If student exist, approve the arrival, create a ticket, then forward to queue for the Nurse to consume

    - Register Student page, with the following functions:

        - Receptionist should be able to upload a picture/pdf document of the student's SIF letter (Student Information Form)

        - The following information should be extracted from the form:

            - First Name

            - Middle Name

            - Last Name

            - Age

            - Reg Number 

            - Faculty

            - Department

            - Level 

            - Phone Number

            - Date of Birth

            the SIF letter will also be kept in a file storage

	    - also, the receptionist should be able to register a student without an SIF letter, but should be able to ad only the information above manually, and have the student complete he information their portal

        - The information will be used to Create a Student Profile, containing:

       	    - all Student Information

	    - All Tickets from subsequent visits of the student

        - Preview a student's profile 

    - Receptionist Profile page:

	- View and edit their profile information

    - An emergency mode button, which allows the receptionist to notify when there is an emergency at the clinic

- a Logout button/Sign out button

- A Right pane showing open tickets in the queue with their statuses

## Constraints

- All activist by the Receptionist will remain in their dashboard, no links or redirects to another roles dashboard 

## resources

- here is a link for an SIF letter sample: https://www.scribd.com/document/456074960/SPS-19-MCE-00083-SIF


# Receptionist dashboard: claude
Lets redo the Rceptionist Dashboard. Following a Neomorphism design style throughout the entirety of the project.

## Context
The core of this application is a ticketting system (uses a message queue), which is created by the Receptionist, then forwarded to the Nurse, then to Doctor, then to either Lab Scientist then back to Doctor then to Pharmacist, or directly to the Pharmacist.

## Tasks
I have provided a `Login page.png`, and images with the design inspiration for the dashboard
Here is what we want:
### BAckend
- Create the login page, implement auth using session tokens
- Modify the models to have fields for path to image they upload, an for the SIF form they upload
- Create missing views, and modify already existing
- Create templates with urls 
### Frontend

- a Side Navbar with the linking to the following pages:
    - Search Sudent page (patient), with the following functions:
        - search a student by clinic code, name or reg number. If student doesnt exist, suggest to register student
        - If student exist, approve the arrival, create a ticket, then forward to queue for the Nurse to consume
    - Register Student page, with the following functions:
        - Receptionist should be able to upload a picture/pdf document of the student's SIF letter (Stuent Information Form)
        - The following information should be extracted from the form:
            - First Name
            - Middle Name
            - Last Name
            - Age
            - Reg Number 
            - Faculty
            - Department
            - Level 
            - Phone Number
            - Date of Birth
            the SIF letter will also be kept in a file storage
        - The information will be used to Create a Student Profile, containing:
            - all Student Information from the SIF form 
	    - All Tickets from subsequent visits of the student
        - Preview a student's profile 
        - Receptionist Profile page:
        - View and edit their profile information
        - An emergency mode button, which allows the receptionist to notify when there is an emergency at the clinic
    - a Logout button/Sign out button
    - A Right pane showing open tickets in the queue with their statuses
    ## Constraints
        - All activist by the Receptionist will remain in their dashboard, no links or redirects to another roles dashboard 
    ## resources
        - here is a link for an SIF letter sample: https://www.scribd.com/document/456074960/SPS-19-MCE-00083-SIF
