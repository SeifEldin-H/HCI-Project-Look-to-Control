
# Look to Control
### One Gaze for Every Device in the Room

## 1. Project Overview

Look to Control is a Human-Computer Interaction (HCI) project exploring an alternative way of controlling smart-home devices through gaze-based interaction.

The project researches how users can select a device by looking towards it and then perform a short, deliberate confirmation action to activate it.

The prototype uses a simulated smart-home environment to explore whether this interaction can make device control more accessible and convenient while reducing accidental activations.

## 2. Problem Statement

Traditional smart-home systems commonly rely on physical switches, remote controls or mobile applications. These methods require users to interact manually with a device or screen.

Gaze-based interaction offers a potential hands-free alternative. However, simply looking at an object does not necessarily mean that a user intends to interact with it.

This creates the **Midas Touch problem**, where ordinary visual attention may be interpreted as an intentional command.

Look to Control explores how separating device selection from activation can help address this problem.

## 3. Research Question

Does looking at a device to select it, followed by a short deliberate action to activate it, allow users to control smart-home devices faster than conventional apps or remotes without causing wrong or accidental actions?

## 4. Proposed Solution

The project explores a visual smart-home dashboard in which users can interact with simulated household devices through gaze or head-directed input.

The proposed interaction consists of:

1. **Default:** Display the available smart-home devices.
2. **Selection:** Identify and highlight the device the user is looking at.
3. **Confirmation:** Require a deliberate action, such as blinking, nodding or speaking.
4. **Activation:** Execute the corresponding simulated device action.
5. **Feedback:** Clearly communicate the resulting device state.

Additional confirmation is particularly important for potentially risky actions, such as unlocking a door.

## 5. Main Design Considerations

The project focuses on the following HCI principles:

- **Accidental activation:** Distinguish ordinary visual attention from intentional commands.
- **Feedback and visibility:** Clearly communicate device selection and activation.
- **Safety:** Introduce confirmation for potentially risky actions.
- **Accessibility:** Consider alternative interaction methods for users who cannot comfortably use gaze, blinking or head movements.
- **Privacy:** Request camera permission and minimise unnecessary storage or transmission of camera data.
- **Consistency:** Maintain predictable interaction behaviour across devices.

## 6. Research and Design

The project investigates existing gaze-based interaction techniques, including the Midas Touch problem, two-stage selection and webcam-based eye tracking.

Initial research includes:

- Jacob (1991) – Eye movements in human-computer interaction.
- DualGaze (2018) – Two-stage gaze selection and confirmation.
- Papoutsaki et al. (2016) – WebGazer and webcam-based eye tracking.

The initial design concepts explore different interface states, device selection, activation feedback, lock confirmation and alternative layouts.

Further research and design refinement will inform the implementation and evaluation of the prototype.

## 7. Prototype and Evaluation

The project aims to develop a simulated smart-home interface for exploring gaze-based device interaction.

The proposed evaluation will compare the prototype with conventional app or remote control methods.

Potential evaluation measures include:

- Task completion time.
- Incorrect device selections.
- Accidental activations.
- User experience and perceived workload.
- Accessibility and interaction difficulties.

The effectiveness of the proposed interaction will need to be established through prototype testing and user evaluation.

## 8. Repository Structure

```text
HCI-Project-Look-to-Control/
│
├── design/
│   ├── README.md
│   └── originals/
│
├── docs/
│   ├── requirements.md
│   └── research.md
│
├── Look-To-Control/
│
├── README.md
└── Implementation files...
```

- **design/** – Initial interface designs, interaction-flow diagrams and alternative layouts.
- **docs/** – Project requirements and supporting research.
- **Look-To-Control/** – Project prototype and related project resources.
- **README.md** – Main project overview and documentation entry point.


## 10. Project Team

- Hamza Elsayed
- Seif Elnady
- Priyam Joshi
- Yuxing Yao

---

*Look to Control – Exploring more intuitive and accessible smart-home interaction through gaze-based control.*
