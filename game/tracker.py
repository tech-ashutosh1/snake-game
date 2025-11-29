import cv2, math
import mediapipe as mp

class HandTracker:
    """Handles hand tracking using MediaPipe with enhanced stability."""

    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1
        )
        self.prev_position = None

    def find_finger_position(self, frame, draw_labels=True):
        """Extract index finger tip position from frame with hand landmarks drawn.

        If draw_labels is False, the tracker will not write textual labels onto the
        frame (e.g. "INDEX" / "NO HAND DETECTED"). This lets the caller draw
        labels separately (for example, to control mirroring of labels).
        """
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(frame_rgb)

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            self.mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_drawing_styles.get_default_hand_landmarks_style(),
                self.mp_drawing_styles.get_default_hand_connections_style()
            )

            index_finger = hand_landmarks.landmark[8]

            h, w, _ = frame.shape
            x = int(index_finger.x * w)
            y = int(index_finger.y * h)

            cv2.circle(frame, (x, y), 10, (0, 255, 0), -1)
            if draw_labels:
                cv2.putText(frame, "INDEX", (x + 15, y), cv2.FONT_HERSHEY_SIMPLEX, 
                            0.5, (0, 255, 0), 2)

            new_pos = (x, y)

            if self.prev_position is not None:
                dist = math.hypot(new_pos[0] - self.prev_position[0], 
                                  new_pos[1] - self.prev_position[1])
                if dist > 200:
                    return self.prev_position, True, frame

            self.prev_position = new_pos
            return new_pos, True, frame

        if draw_labels:
            cv2.putText(frame, "NO HAND DETECTED", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return self.prev_position, False, frame
