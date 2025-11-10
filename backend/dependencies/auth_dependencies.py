from fastapi import Depends, status
from utils.auth_helper import decode_token
from fastapi.security import OAuth2PasswordBearer
from db.database import get_session
from sqlmodel import Session, select
from db.models import User, LoginSession, UserType
from utils.procedures import CustomError
import os
from dotenv import load_dotenv

load_dotenv()

PRIVATE_MODE = os.getenv('PRIVATE_MODE', 'false').lower() == 'true'

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='apps/auth/login') if not PRIVATE_MODE else None


def _get_or_create_local_user(db: Session) -> User:
    user = db.exec(select(User).where(User.email == 'local@neuralagent')).first()
    if user:
        return user
    user = User(
        name='Local User',
        email='local@neuralagent',
        user_type=UserType.NORMAL_USER,
        is_email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user_dependency(token: str = Depends(oauth2_scheme) if not PRIVATE_MODE else None, db: Session = Depends(get_session)):
    if PRIVATE_MODE:
        # Bypass auth, return or create a single local user
        return _get_or_create_local_user(db)

    try:
        payload = decode_token(token)
        user_id = payload.get('user_id')

        u_query = select(User).where(User.id == user_id)
        user = db.exec(u_query).first()

        if not user:
            raise CustomError(status_code=status.HTTP_401_UNAUTHORIZED, message='Invalid_Token')

        session_id = payload.get('session_id')
        s_query = select(LoginSession).where(LoginSession.id == session_id)
        login_session = db.exec(s_query).first()

        if not login_session or login_session.is_logged_out is True:
            raise CustomError(status_code=status.HTTP_401_UNAUTHORIZED, message='Invalid_Token')

        if user.is_blocked is True:
            raise CustomError(status_code=status.HTTP_403_FORBIDDEN, message='You_Are_Blocked')

        return user

    except Exception:
        raise CustomError(status_code=status.HTTP_401_UNAUTHORIZED, message='Invalid_Token')
