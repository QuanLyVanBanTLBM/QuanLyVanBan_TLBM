import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from '@i18n/translate';

export interface LoginCharactersProps {
  isUsernameFocused: boolean;
  isPasswordFocused: boolean;
  showPassword: boolean;
  isTyping: boolean;
  isSuccess: boolean;
  isError: boolean;
}

export const LoginCharacters: React.FC<LoginCharactersProps> = ({
  isUsernameFocused,
  isPasswordFocused,
  showPassword,
  isTyping,
  isSuccess,
  isError,
}) => {
  const { t } = useTranslation();
  const [clickedChar, setClickedChar] = useState<string | null>(null);
  const [mousePos, setMousePos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Refs của các cụm mắt nhân vật
  const purpleEyesRef = useRef<HTMLDivElement>(null);
  const blackEyesRef = useRef<HTMLDivElement>(null);
  const orangeEyesRef = useRef<HTMLDivElement>(null);
  const yellowEyesRef = useRef<HTMLDivElement>(null);

  // Lắng nghe di chuột toàn màn hình để con ngươi liếc theo chuột
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const [pupilOffsets, setPupilOffsets] = useState({
    purple: { x: 0, y: 0 },
    black: { x: 0, y: 0 },
    orange: { x: 0, y: 0 },
    yellow: { x: 0, y: 0 },
  });

  useEffect(() => {
    const calculateOffset = (eyeElem: HTMLElement | null, maxOffset: number = 6) => {
      if (!eyeElem) return { x: 0, y: 0 };
      if (isUsernameFocused) {
        return { x: maxOffset * 0.95, y: 0 };
      }
      const rect = eyeElem.getBoundingClientRect();
      const eyeCenterX = rect.left + rect.width / 2;
      const eyeCenterY = rect.top + rect.height / 2;

      const deltaX = mousePos.x - eyeCenterX;
      const deltaY = mousePos.y - eyeCenterY;
      const angle = Math.atan2(deltaY, deltaX);
      const distance = Math.min(maxOffset, Math.hypot(deltaX, deltaY) / 28);

      return {
        x: Math.round(Math.cos(angle) * distance * 100) / 100,
        y: Math.round(Math.sin(angle) * distance * 100) / 100,
      };
    };

    setPupilOffsets({
      purple: calculateOffset(purpleEyesRef.current, 5),
      black: calculateOffset(blackEyesRef.current, 7),
      orange: calculateOffset(orangeEyesRef.current, 6),
      yellow: calculateOffset(yellowEyesRef.current, 5),
    });
  }, [mousePos, isUsernameFocused]);

  const handleCharClick = (charName: string) => {
    setClickedChar(charName);
    setTimeout(() => setClickedChar(null), 550);
  };

  const isEyesClosed = isPasswordFocused && !showPassword;
  const isShocked = isPasswordFocused && showPassword;

  return (
    <div className="w-full md:w-[45%] bg-surface-elevated !rounded-none !shadow-none !border-0 md:!border-r md:!border-solid md:!border-border-subtle relative flex flex-col justify-between p-4 sm:p-5 md:p-6 select-none overflow-hidden min-h-[230px] sm:min-h-[260px] md:min-h-[380px]">
      {/* Tiêu đề thương hiệu phân hệ */}
      <div className="flex items-center gap-2.5 z-10">
        <div className="w-10 h-10 rounded-lg bg-surface border border-subtle flex items-center justify-center shadow-sm p-1.5 shrink-0">
          <img src="/baolong-icon.png" alt="Bảo Long Icon" className="w-full h-full object-contain" />
        </div>
        <div>
          <div className="text-sm font-extrabold text-main leading-tight">
            {t('auth.brandTitle')}
          </div>
          <div className="text-[11px] font-bold text-primary tracking-wide">
            {t('auth.brandSubtitle')}
          </div>
        </div>
      </div>

      {/* CỤM 4 NHÂN VẬT HOẠT HỌA CÓ ANIMATION TƯƠNG TÁC */}
      <div
        className={`character-cluster scale-[0.74] sm:scale-[0.82] md:scale-[0.88] origin-bottom-left ${
          isError ? 'is-error' : ''
        } ${isSuccess ? 'is-success' : ''}`}
      >
        {/* 1. NHÂN VẬT TÍM (Hình chữ nhật) */}
        <div className="char-bobber bobber-purple">
          <div
            className={`char-purple ${isEyesClosed ? 'eyes-closed' : ''} ${isShocked ? 'shocked' : ''} ${
              clickedChar === 'purple' ? 'clicked' : ''
            } ${isTyping ? 'typing' : ''}`}
            onClick={() => handleCharClick('purple')}
            title={t('auth.characters.purple')}
          >
            <div className="purple-eyes" ref={purpleEyesRef}>
              <div className={`eye-socket-purple ${isEyesClosed ? 'closed' : ''}`}>
                <div
                  className="pupil-purple"
                  style={{ transform: `translate3d(${pupilOffsets.purple.x}px, ${pupilOffsets.purple.y}px, 0)` }}
                />
              </div>
              <div className={`eye-socket-purple ${isEyesClosed ? 'closed' : ''}`}>
                <div
                  className="pupil-purple"
                  style={{ transform: `translate3d(${pupilOffsets.purple.x}px, ${pupilOffsets.purple.y}px, 0)` }}
                />
              </div>
            </div>
            <div className={`purple-mouth ${isShocked ? 'shocked' : ''}`} />
          </div>
        </div>

        {/* 2. NHÂN VẬT ĐEN (Trụ tròn to) */}
        <div className="char-bobber bobber-black">
          <div
            className={`char-black ${isEyesClosed ? 'eyes-closed' : ''} ${isShocked ? 'shocked' : ''} ${
              clickedChar === 'black' ? 'clicked' : ''
            } ${isTyping ? 'typing' : ''}`}
            onClick={() => handleCharClick('black')}
            title={t('auth.characters.black')}
          >
            <div className="black-eyes" ref={blackEyesRef}>
              <div className={`black-eye-sclera ${isEyesClosed ? 'closed' : ''} ${isShocked ? 'shocked' : ''}`}>
                <div
                  className="black-pupil"
                  style={{ transform: `translate3d(${pupilOffsets.black.x}px, ${pupilOffsets.black.y}px, 0)` }}
                />
              </div>
              <div className={`black-eye-sclera ${isEyesClosed ? 'closed' : ''} ${isShocked ? 'shocked' : ''}`}>
                <div
                  className="black-pupil"
                  style={{ transform: `translate3d(${pupilOffsets.black.x}px, ${pupilOffsets.black.y}px, 0)` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* 3. NHÂN VẬT CAM (Bán nguyệt có má hồng & miệng cười) */}
        <div className="char-bobber bobber-orange">
          <div
            className={`char-orange ${isEyesClosed ? 'eyes-closed' : ''} ${isShocked ? 'shocked' : ''} ${
              clickedChar === 'orange' ? 'clicked' : ''
            } ${isTyping ? 'typing' : ''}`}
            onClick={() => handleCharClick('orange')}
            title={t('auth.characters.orange')}
          >
            <div className="orange-eyes-row" ref={orangeEyesRef}>
              <div className="orange-blush-left" style={{ opacity: isEyesClosed ? 0.7 : 0.15 }} />
              <div className={`eye-socket-orange ${isEyesClosed ? 'closed' : ''}`}>
                <div
                  className="pupil-orange"
                  style={{ transform: `translate3d(${pupilOffsets.orange.x}px, ${pupilOffsets.orange.y}px, 0)` }}
                />
              </div>
              <div className={`eye-socket-orange ${isEyesClosed ? 'closed' : ''}`}>
                <div
                  className="pupil-orange"
                  style={{ transform: `translate3d(${pupilOffsets.orange.x}px, ${pupilOffsets.orange.y}px, 0)` }}
                />
              </div>
              <div className="orange-blush-right" style={{ opacity: isEyesClosed ? 0.7 : 0.15 }} />
            </div>
            <div className={`orange-mouth ${isShocked ? 'shocked' : ''}`} />
          </div>
        </div>

        {/* 4. NHÂN VẬT VÀNG (Mái vòm có đường miệng ngang) */}
        <div className="char-bobber bobber-yellow">
          <div
            className={`char-yellow ${isEyesClosed ? 'eyes-closed' : ''} ${isShocked ? 'shocked' : ''} ${
              clickedChar === 'yellow' ? 'clicked' : ''
            } ${isTyping ? 'typing' : ''}`}
            onClick={() => handleCharClick('yellow')}
            title={t('auth.characters.yellow')}
          >
            <div className="yellow-eyes" ref={yellowEyesRef}>
              <div className={`eye-socket-yellow ${isEyesClosed ? 'closed' : ''}`}>
                <div
                  className="pupil-yellow"
                  style={{ transform: `translate3d(${pupilOffsets.yellow.x}px, ${pupilOffsets.yellow.y}px, 0)` }}
                />
              </div>
            </div>
            <div className={`yellow-mouth-line ${isShocked ? 'shocked' : ''}`} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginCharacters;


