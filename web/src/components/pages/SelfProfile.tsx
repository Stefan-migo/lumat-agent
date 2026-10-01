import { useState, type FormEvent } from "react";
import { ApiError, changePassword, fetchMe, updateMe } from "../../api";
import { useAsyncData } from "../../hooks/useAsyncData";
import { roleLabels } from "../../roleLabels";
import { Avatar } from "../primitives/Avatar";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Input } from "../primitives/Input";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";

type Feedback = { tone: "success" | "danger"; title: string };

export function SelfProfile() {
  const profileData = useAsyncData(fetchMe);
  const profile = profileData.data;
  const [draft, setDraft] = useState<{ name: string; phone: string } | null>(null);
  const [cleared, setCleared] = useState<{ name: boolean; phone: boolean }>({ name: false, phone: false });
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileFeedback, setProfileFeedback] = useState<Feedback | null>(null);
  const [password, setPassword] = useState({ current_password: "", new_password: "" });
  const [savingPassword, setSavingPassword] = useState(false);
  const [passwordFeedback, setPasswordFeedback] = useState<Feedback | null>(null);
  const fields = draft ?? { name: profile?.name ?? "", phone: profile?.phone ?? "" };

  const saveProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!profile || savingProfile) return;
    const body = {
      name: cleared.name ? null : fields.name.trim(),
      phone: cleared.phone ? null : fields.phone.trim(),
    };
    if ((!cleared.name && !body.name && profile.name !== null) || (!cleared.phone && !body.phone && profile.phone !== null)) {
      setProfileFeedback({ tone: "danger", title: "Usa “Borrar” para quitar un dato; no dejes el campo vacío." });
      return;
    }
    setSavingProfile(true);
    setProfileFeedback(null);
    try {
      await updateMe(body);
      setDraft({ name: body.name ?? "", phone: body.phone ?? "" });
      setCleared({ name: false, phone: false });
      setProfileFeedback({ tone: "success", title: "Datos personales guardados" });
    } catch {
      setProfileFeedback({ tone: "danger", title: "No pudimos guardar tus datos personales." });
    } finally {
      setSavingProfile(false);
    }
  };

  const savePassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (savingPassword) return;
    setSavingPassword(true);
    setPasswordFeedback(null);
    try {
      await changePassword(password);
      setPassword({ current_password: "", new_password: "" });
      setPasswordFeedback({ tone: "success", title: "Contraseña actualizada" });
    } catch (error) {
      const title = error instanceof ApiError && error.status === 401
        ? "La contraseña actual no es correcta."
        : error instanceof ApiError && error.status === 422
          ? "La nueva contraseña debe tener al menos 8 caracteres."
          : "No pudimos cambiar tu contraseña.";
      setPasswordFeedback({ tone: "danger", title });
    } finally {
      setSavingPassword(false);
    }
  };

  const loadingState = profileData.state === "loading"
    ? <StateMessage tone="info" role="status" spinner title="Cargando tu perfil" />
    : profileData.state === "error" || profileData.state === "denied"
      ? <StateMessage tone="danger" role="alert" title="No pudimos cargar tu perfil" detail="Inténtalo nuevamente." />
      : undefined;

  return (
    <PageFrame title="Mi perfil" meta="Tus datos personales y acceso" state={loadingState}>
      {!profile ? null : <div className="detail-region">
        <section className="detail-region__rail" aria-label="Identidad">
          <Card title="Tu cuenta">
            <div className="client-ficha__customer-controls">
              <Avatar name={profile.username} />
              <strong>{profile.username}</strong>
              <span>{roleLabels[profile.role]}</span>
            </div>
          </Card>
        </section>
        <div className="detail-region__main">
          <Card title="Datos personales">
            <form onSubmit={(event) => void saveProfile(event)}>
              <Input label="Nombre" value={fields.name} onChange={(event) => { setDraft({ ...fields, name: event.target.value }); setCleared({ ...cleared, name: false }); }} />
              <Button type="button" variant="secondary" onClick={() => { setDraft({ ...fields, name: "" }); setCleared({ ...cleared, name: true }); }}>Borrar nombre</Button>
              <Input label="Teléfono" type="tel" value={fields.phone} onChange={(event) => { setDraft({ ...fields, phone: event.target.value }); setCleared({ ...cleared, phone: false }); }} />
              <Button type="button" variant="secondary" onClick={() => { setDraft({ ...fields, phone: "" }); setCleared({ ...cleared, phone: true }); }}>Borrar teléfono</Button>
              {profileFeedback ? <StateMessage tone={profileFeedback.tone} role={profileFeedback.tone === "danger" ? "alert" : "status"} title={profileFeedback.title} /> : null}
              <Button type="submit" disabled={savingProfile}>{savingProfile ? "Guardando…" : "Guardar cambios"}</Button>
            </form>
          </Card>
          <Card title="Cambiar contraseña">
            <form onSubmit={(event) => void savePassword(event)}>
              <Input label="Contraseña actual" type="password" autoComplete="current-password" required value={password.current_password} onChange={(event) => setPassword({ ...password, current_password: event.target.value })} />
              <Input label="Nueva contraseña" type="password" autoComplete="new-password" minLength={8} required value={password.new_password} onChange={(event) => setPassword({ ...password, new_password: event.target.value })} />
              {passwordFeedback ? <StateMessage tone={passwordFeedback.tone} role={passwordFeedback.tone === "danger" ? "alert" : "status"} title={passwordFeedback.title} /> : null}
              <Button type="submit" disabled={savingPassword}>{savingPassword ? "Actualizando…" : "Cambiar contraseña"}</Button>
            </form>
          </Card>
        </div>
      </div>}
    </PageFrame>
  );
}
