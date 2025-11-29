import sqlite3
import numpy as np
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
import pickle
import os


MODEL_DIR = "models"

if not os.path.exists(MODEL_DIR):
    os.makedirs(MODEL_DIR)


def get_user_data(user_id):
    """
    تسحب بيانات المستخدم من جدول keystrokes
    وتستخدم فقط dwell و flight كـ features.
    """
    conn = sqlite3.connect("project.db")
    cur = conn.cursor()
    cur.execute(
        "SELECT dwell, flight FROM keystrokes WHERE user_id=?",
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return np.empty((0, 2))

    data = np.array(rows, dtype=float)

    # إزالة الصفوف اللي فيها NaN (مثلاً أول ضغطة flight فيها None)
    data = data[~np.isnan(data).any(axis=1)]

    return data


def train_user(user_id):
    """
    تدريب نموذج One-Class SVM على بيانات المستخدم.
    """
    data = get_user_data(user_id)

    # لازم عدد كافي من العينات
    if len(data) < 20:
        return False

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(data)

    model = OneClassSVM(kernel="rbf", nu=0.1, gamma="scale")
    model.fit(X_scaled)

    model_path = os.path.join(MODEL_DIR, f"user_{user_id}.pkl")
    with open(model_path, "wb") as f:
        pickle.dump({"model": model, "scaler": scaler}, f)

    return True


def verify_user_keystrokes(user_id, samples):
    """
    يستقبل samples بالشكل:
    [
        [dwell1, flight1],
        [dwell2, flight2],
        ...
    ]
    ويرجّع True/False حسب نسبة العينات المقبولة.
    """
    print("VERIFY CALLED", user_id, "len:", len(samples))

    model_path = os.path.join(MODEL_DIR, f"user_{user_id}.pkl")
    if not os.path.exists(model_path):
        return False

    with open(model_path, "rb") as f:
        bundle = pickle.load(f)

    model = bundle["model"]
    scaler = bundle["scaler"]

    samples = np.array(samples, dtype=float)
    samples = samples[~np.isnan(samples).any(axis=1)]

    if len(samples) == 0:
        return False

    X_scaled = scaler.transform(samples)
    preds = model.predict(X_scaled)  # 1 = inlier, -1 = outlier
    score = np.mean(preds == 1)

    print("SCORE:", score, "SAMPLES:", len(samples))

    # عتبة مبدئية 0.5
    return score >= 0.3
