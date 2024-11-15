from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(String, primary_key=True)
    name = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime, nullable=True)
    status = Column(String)
    tags = Column(JSON)
    pipeline_config = Column(JSON, nullable=True)
    components = relationship("PipelineComponent", back_populates="experiment")


class PipelineComponent(Base):
    __tablename__ = "pipeline_components"

    id = Column(Integer, primary_key=True)
    experiment_id = Column(String, ForeignKey("experiments.id"))
    name = Column(String)
    type = Column(String)
    stage = Column(String)
    position = Column(Integer)

    experiment = relationship("Experiment", back_populates="components")
