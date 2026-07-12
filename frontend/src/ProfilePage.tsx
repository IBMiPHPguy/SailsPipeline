import { ChangeEvent, FormEvent, useEffect, useId, useRef, useState } from "react";
import {
  deleteCurrentUserAvatar,
  fetchCurrentUser,
  updateCurrentUserSignature,
  uploadCurrentUserAvatar,
  uploadCurrentUserSignatureImage,
} from "./authApi";
import AvatarCropModal from "./AvatarCropModal";
import { resolveStaticAssetUrl } from "./portalBranding";
import RichTextEditor from "./RichTextEditor";
import type { User } from "./types";
import {
  formatRoleLabel,
  formatUsernameDisplayName,
  initialsFromUsername,
  usernameFirstLast,
} from "./userDisplay";

type ProfilePageProps = {
  currentUser: User;
  onUserUpdated: (user: User) => void;
};

type ProfileToast = {
  tone: "success" | "error";
  text: string;
};

const TOAST_DISMISS_MS = 4000;

export default function ProfilePage({ currentUser, onUserUpdated }: ProfilePageProps) {
  const fileInputId = useId();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const toastTimerRef = useRef<number | null>(null);
  const { firstName, lastName } = usernameFirstLast(currentUser.username);
  const displayName = formatUsernameDisplayName(currentUser.username) || currentUser.username;
  const initials = initialsFromUsername(currentUser.username);
  const avatarSrc = resolveStaticAssetUrl(currentUser.avatar_url);

  const [signatureDraft, setSignatureDraft] = useState(currentUser.email_signature_block ?? "");
  const [savingSignature, setSavingSignature] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [removingAvatar, setRemovingAvatar] = useState(false);
  const [cropFile, setCropFile] = useState<File | null>(null);
  const [toast, setToast] = useState<ProfileToast | null>(null);

  useEffect(() => {
    setSignatureDraft(currentUser.email_signature_block ?? "");
  }, [currentUser.email_signature_block, currentUser.id]);

  useEffect(() => {
    return () => {
      if (toastTimerRef.current !== null) {
        window.clearTimeout(toastTimerRef.current);
      }
    };
  }, []);

  function showToast(next: ProfileToast) {
    if (toastTimerRef.current !== null) {
      window.clearTimeout(toastTimerRef.current);
    }
    setToast(next);
    toastTimerRef.current = window.setTimeout(() => {
      setToast(null);
      toastTimerRef.current = null;
    }, TOAST_DISMISS_MS);
  }

  async function refreshUser() {
    const user = await fetchCurrentUser();
    onUserUpdated(user);
    setSignatureDraft(user.email_signature_block ?? "");
    return user;
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }
    const looksLikeImage =
      file.type.startsWith("image/") ||
      /\.(jpe?g|png|gif|webp|bmp)$/i.test(file.name);
    if (!looksLikeImage) {
      showToast({ tone: "error", text: "Please choose an image file for your headshot." });
      return;
    }
    setCropFile(file);
  }

  function closeCropModal() {
    setCropFile(null);
  }

  async function handleCropConfirm(blob: Blob) {
    setUploadingAvatar(true);
    try {
      await uploadCurrentUserAvatar(blob, "avatar.png");
      await refreshUser();
      showToast({ tone: "success", text: "Headshot updated." });
      closeCropModal();
    } catch (uploadError) {
      showToast({
        tone: "error",
        text: uploadError instanceof Error ? uploadError.message : "Unable to upload headshot.",
      });
    } finally {
      setUploadingAvatar(false);
    }
  }

  async function handleRemoveAvatar() {
    if (removingAvatar) {
      return;
    }
    setRemovingAvatar(true);
    try {
      const user = await deleteCurrentUserAvatar();
      onUserUpdated(user);
      showToast({ tone: "success", text: "Headshot removed." });
    } catch (removeError) {
      showToast({
        tone: "error",
        text: removeError instanceof Error ? removeError.message : "Unable to remove headshot.",
      });
    } finally {
      setRemovingAvatar(false);
    }
  }

  async function handleSaveSignature(event: FormEvent) {
    event.preventDefault();
    if (savingSignature) {
      return;
    }
    setSavingSignature(true);
    try {
      const normalized = signatureDraft.trim() || null;
      const user = await updateCurrentUserSignature(normalized);
      onUserUpdated(user);
      setSignatureDraft(user.email_signature_block ?? "");
      showToast({ tone: "success", text: "Email signature saved." });
    } catch (saveError) {
      showToast({
        tone: "error",
        text: saveError instanceof Error ? saveError.message : "Unable to save signature.",
      });
    } finally {
      setSavingSignature(false);
    }
  }

  return (
    <div className="profile-page">
      <section className="card section-card">
        <header className="section-card-header">
          <div>
            <h2>Profile</h2>
            <p className="muted">Your account details, headshot, and outbound email signature.</p>
          </div>
        </header>
      </section>

      <section className="card section-card">
        <header className="section-card-header">
          <div>
            <h3>Account</h3>
            <p className="muted">Read-only details derived from your login.</p>
          </div>
        </header>
        <div className="section-card-body profile-readonly-grid">
          <div>
            <span className="profile-field-label">First name</span>
            <p className="profile-field-value">{firstName || "—"}</p>
          </div>
          <div>
            <span className="profile-field-label">Last name</span>
            <p className="profile-field-value">{lastName || "—"}</p>
          </div>
          <div>
            <span className="profile-field-label">Username</span>
            <p className="profile-field-value">{currentUser.username}</p>
          </div>
          <div className="profile-field-email">
            <span className="profile-field-label">Email</span>
            <p className="profile-field-value">{currentUser.email}</p>
          </div>
          <div>
            <span className="profile-field-label">Role</span>
            <p className="profile-field-value">{formatRoleLabel(currentUser.role)}</p>
          </div>
        </div>
      </section>

      <section className="card section-card">
        <header className="section-card-header">
          <div>
            <h3>Headshot</h3>
            <p className="muted">Shown in the header avatar. Without a photo, your initials are used.</p>
          </div>
        </header>
        <div className="section-card-body profile-headshot-row">
          <div className="profile-headshot-preview" title={displayName} aria-label={displayName}>
            {avatarSrc ? (
              <img src={avatarSrc} alt="" className="profile-headshot-image" />
            ) : (
              <span className="profile-headshot-initials" aria-hidden="true">
                {initials}
              </span>
            )}
          </div>
          <div className="profile-headshot-actions">
            <input
              ref={fileInputRef}
              id={fileInputId}
              type="file"
              accept="image/*"
              className="sr-only"
              onChange={handleFileChange}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadingAvatar || removingAvatar}
            >
              Upload headshot
            </button>
            {avatarSrc ? (
              <button
                type="button"
                className="secondary-button"
                onClick={() => void handleRemoveAvatar()}
                disabled={uploadingAvatar || removingAvatar}
              >
                {removingAvatar ? "Removing…" : "Remove headshot"}
              </button>
            ) : null}
          </div>
        </div>
      </section>

      <section className="card section-card">
        <header className="section-card-header">
          <div>
            <h3>Email signature</h3>
            <p className="muted">Appended to outbound emails you send from SailsPipeline.</p>
          </div>
        </header>
        <form className="section-card-body profile-signature-form" onSubmit={(event) => void handleSaveSignature(event)}>
          <div className="agency-settings-full-width agency-settings-rich-text-field">
            <span className="agency-settings-field-label">Signature</span>
            <RichTextEditor
              value={signatureDraft}
              onChange={setSignatureDraft}
              uploadImage={async (file) => {
                const result = await uploadCurrentUserSignatureImage(file);
                return result.image_url;
              }}
              placeholder="Kind regards, your name, phone, and logo…"
              disabled={savingSignature}
              minHeight="12rem"
              ariaLabel="Email signature"
            />
            <p className="muted agency-settings-rich-text-hint">
              Images are uploaded to secure storage (not embedded), so large signatures save reliably.
            </p>
          </div>
          <div className="profile-signature-actions">
            <button type="submit" disabled={savingSignature}>
              {savingSignature ? "Saving…" : "Save signature"}
            </button>
          </div>
        </form>
      </section>

      {cropFile ? (
        <AvatarCropModal
          imageFile={cropFile}
          confirming={uploadingAvatar}
          onCancel={closeCropModal}
          onConfirm={handleCropConfirm}
        />
      ) : null}

      {toast ? (
        <div
          className={`register-toast register-toast-top${toast.tone === "error" ? " register-toast-error" : ""}`}
          role={toast.tone === "error" ? "alert" : "status"}
          aria-live={toast.tone === "error" ? "assertive" : "polite"}
        >
          <span className="register-toast-icon" aria-hidden="true">
            {toast.tone === "error" ? "!" : "✓"}
          </span>
          <span>{toast.text}</span>
        </div>
      ) : null}
    </div>
  );
}
