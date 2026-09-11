"""
backend/models/db_models.py

SQLAlchemy models for persisting emergencies. Uses SQLite for simplicity;
swapping to MySQL later would only require changing the connection string
in app.py, since SQLAlchemy abstracts the database engine.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Emergency(db.Model):
    __tablename__ = "emergencies"

    id = db.Column(db.Integer, primary_key=True)
    emergency_node = db.Column(db.String(5), nullable=False)
    hour = db.Column(db.Integer, nullable=False)
    day = db.Column(db.String(10), nullable=False)

    hospital_id = db.Column(db.String(10), nullable=False)
    hospital_name = db.Column(db.String(100), nullable=False)
    route = db.Column(db.String(50), nullable=False)  # stored as "A->D->G"
    predicted_travel_time = db.Column(db.Float, nullable=False)

    rerouted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "emergency_node": self.emergency_node,
            "hour": self.hour,
            "day": self.day,
            "hospital_id": self.hospital_id,
            "hospital_name": self.hospital_name,
            "route": self.route,
            "predicted_travel_time": self.predicted_travel_time,
            "rerouted": self.rerouted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }