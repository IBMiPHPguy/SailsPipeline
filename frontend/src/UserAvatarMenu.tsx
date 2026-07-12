import { useEffect, useRef, useState } from "react";
import { resolveStaticAssetUrl } from "./portalBranding";
import type { User } from "./types";
import { formatUsernameDisplayName, initialsFromUsername } from "./userDisplay";

type UserAvatarMenuProps = {
  user: User;
  onProfile: () => void;
  onSignOff: () => void;
};

export default function UserAvatarMenu({ user, onProfile, onSignOff }: UserAvatarMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const displayName = formatUsernameDisplayName(user.username) || user.username;
  const initials = initialsFromUsername(user.username);
  const avatarSrc = resolveStaticAssetUrl(user.avatar_url);

  useEffect(() => {
    if (!open) {
      return;
    }

    function handlePointerDown(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div className="user-avatar-menu" ref={rootRef}>
      <button
        type="button"
        className="user-avatar-button"
        title={displayName}
        aria-label={`${displayName} account menu`}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        {avatarSrc ? (
          <img src={avatarSrc} alt="" className="user-avatar-image" />
        ) : (
          <span className="user-avatar-initials" aria-hidden="true">
            {initials}
          </span>
        )}
      </button>

      {open ? (
        <div className="user-avatar-dropdown" role="menu">
          <button
            type="button"
            role="menuitem"
            className="user-avatar-dropdown-item"
            onClick={() => {
              setOpen(false);
              onProfile();
            }}
          >
            Profile
          </button>
          <button
            type="button"
            role="menuitem"
            className="user-avatar-dropdown-item"
            onClick={() => {
              setOpen(false);
              onSignOff();
            }}
          >
            Sign Off
          </button>
        </div>
      ) : null}
    </div>
  );
}
