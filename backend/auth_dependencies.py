from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import PyJWTError
from sqlalchemy.orm import Session

from db import get_db
from models import User
from security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='authentication required',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    try:
        token_payload = decode_token(credentials.credentials)
        user_id = int(token_payload['sub'])
    except (KeyError, TypeError, ValueError, PyJWTError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='invalid authentication token',
            headers={'WWW-Authenticate': 'Bearer'},
        ) from None

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='user not found or inactive')
    return user


def require_hr_user(user: User = Depends(get_current_user)) -> User:
    if user.role not in {'ADMIN', 'HR_MANAGER', 'RECRUITER'}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='HR role required')
    return user
