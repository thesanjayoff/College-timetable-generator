from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_read_access, require_write_access
from app.models.college import Section
from app.models.elective import ElectiveBasket, ElectiveOption, ElectiveParticipation
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.schemas.elective import (
    ElectiveBasketCreate,
    ElectiveBasketOut,
    ElectiveBasketUpdate,
    ElectiveOptionNestedCreate,
    ElectiveOptionOut,
    ElectiveOptionUpdate,
    ElectiveParticipationNestedCreate,
    ElectiveParticipationOut,
)

router = APIRouter(prefix="/api/electives", tags=["electives"])


def _get_basket_or_404(db: Session, basket_id: int) -> ElectiveBasket:
    basket = db.get(ElectiveBasket, basket_id)
    if basket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ElectiveBasket not found")
    return basket


# ---- Baskets ----

@router.get("/baskets", response_model=list[ElectiveBasketOut], dependencies=[Depends(require_read_access)])
def list_baskets(db: Session = Depends(get_db)):
    return db.query(ElectiveBasket).order_by(ElectiveBasket.id).all()


@router.get("/baskets/{basket_id}", response_model=ElectiveBasketOut, dependencies=[Depends(require_read_access)])
def get_basket(basket_id: int, db: Session = Depends(get_db)):
    return _get_basket_or_404(db, basket_id)


@router.post("/baskets", response_model=ElectiveBasketOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_write_access)])
def create_basket(payload: ElectiveBasketCreate, db: Session = Depends(get_db)):
    basket = ElectiveBasket(**payload.model_dump())
    db.add(basket)
    db.commit()
    db.refresh(basket)
    return basket


@router.put("/baskets/{basket_id}", response_model=ElectiveBasketOut, dependencies=[Depends(require_write_access)])
def update_basket(basket_id: int, payload: ElectiveBasketUpdate, db: Session = Depends(get_db)):
    basket = _get_basket_or_404(db, basket_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(basket, field, value)
    db.commit()
    db.refresh(basket)
    return basket


@router.delete("/baskets/{basket_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def delete_basket(basket_id: int, db: Session = Depends(get_db)):
    basket = _get_basket_or_404(db, basket_id)
    db.delete(basket)
    db.commit()
    return None


# ---- Options (nested under basket) ----

@router.get("/baskets/{basket_id}/options", response_model=list[ElectiveOptionOut],
            dependencies=[Depends(require_read_access)])
def list_options(basket_id: int, db: Session = Depends(get_db)):
    _get_basket_or_404(db, basket_id)
    return db.query(ElectiveOption).filter(ElectiveOption.basket_id == basket_id).order_by(
        ElectiveOption.id
    ).all()


@router.post("/baskets/{basket_id}/options", response_model=ElectiveOptionOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_write_access)])
def create_option(basket_id: int, payload: ElectiveOptionNestedCreate, db: Session = Depends(get_db)):
    _get_basket_or_404(db, basket_id)
    if db.get(Subject, payload.subject_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    if payload.teacher_id is not None and db.get(Teacher, payload.teacher_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")
    option = ElectiveOption(basket_id=basket_id, **payload.model_dump())
    db.add(option)
    db.commit()
    db.refresh(option)
    return option


@router.put("/baskets/{basket_id}/options/{option_id}", response_model=ElectiveOptionOut,
            dependencies=[Depends(require_write_access)])
def update_option(basket_id: int, option_id: int, payload: ElectiveOptionUpdate, db: Session = Depends(get_db)):
    _get_basket_or_404(db, basket_id)
    option = db.get(ElectiveOption, option_id)
    if option is None or option.basket_id != basket_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ElectiveOption not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("subject_id") is not None and db.get(Subject, data["subject_id"]) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    if data.get("teacher_id") is not None and db.get(Teacher, data["teacher_id"]) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")
    for field, value in data.items():
        setattr(option, field, value)
    db.commit()
    db.refresh(option)
    return option


@router.delete("/baskets/{basket_id}/options/{option_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def delete_option(basket_id: int, option_id: int, db: Session = Depends(get_db)):
    _get_basket_or_404(db, basket_id)
    option = db.get(ElectiveOption, option_id)
    if option is None or option.basket_id != basket_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ElectiveOption not found")
    db.delete(option)
    db.commit()
    return None


# ---- Participations (nested under basket) ----

@router.get("/baskets/{basket_id}/participations", response_model=list[ElectiveParticipationOut],
            dependencies=[Depends(require_read_access)])
def list_participations(basket_id: int, db: Session = Depends(get_db)):
    _get_basket_or_404(db, basket_id)
    return db.query(ElectiveParticipation).filter(
        ElectiveParticipation.basket_id == basket_id
    ).order_by(ElectiveParticipation.id).all()


@router.post("/baskets/{basket_id}/participations", response_model=ElectiveParticipationOut,
             status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_write_access)])
def create_participation(
    basket_id: int, payload: ElectiveParticipationNestedCreate, db: Session = Depends(get_db)
):
    _get_basket_or_404(db, basket_id)
    if db.get(Section, payload.section_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    participation = ElectiveParticipation(basket_id=basket_id, section_id=payload.section_id)
    db.add(participation)
    db.commit()
    db.refresh(participation)
    return participation


@router.delete("/baskets/{basket_id}/participations/{participation_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_write_access)])
def delete_participation(basket_id: int, participation_id: int, db: Session = Depends(get_db)):
    _get_basket_or_404(db, basket_id)
    participation = db.get(ElectiveParticipation, participation_id)
    if participation is None or participation.basket_id != basket_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ElectiveParticipation not found")
    db.delete(participation)
    db.commit()
    return None
