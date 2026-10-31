import { useState, type FormEvent } from "react";
import { LockKeyhole, Phone, Save, ShieldCheck, UserRound } from "lucide-react";
import { ApiError, changePassword, fetchMe, updateMe } from "../../api";
import { useAsyncData } from "../../hooks/useAsyncData";
import { roleLabels } from "../../roleLabels";
import { Avatar } from "../primitives/Avatar";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { useToast } from "../primitives/Toast";
import { Card } from "../primitives/Card";
import { Icon } from "../primitives/Icon";
import { Input } from "../primitives/Input";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";

export function SelfProfile() {
  const toast = useToast();
  const profileData = useAsyncData(fetchMe);
  const profile = profileData.data;
  const [draft, setDraft] = useState<{ name: string; phone: string } | null>(null);
  const [savingProfile, setSavingProfile] = useState(false);
  const [password, setPassword] = useState({ current_password: "", new_password: "" });
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [savingPassword, setSavingPassword] = useState(false);
  const fields = draft ?? { name: profile?.name ?? "", phone: profile?.phone ?? "" };

  const discardProfile = () => {
    setDraft({ name: profile?.name ?? "", phone: profile?.phone ?? "" });
  };

  const saveProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!profile || savingProfile) return;
    setSavingProfile(true);
    const name = fields.name.trim();
    const phone = fields.phone.trim();
    try {
      await updateMe({ name: name || null, phone: phone || null });
      setDraft({ name, phone });
      toast.show("Datos personales guardados.");
    } catch {
      toast.show("No pudimos guardar tus datos personales.", "danger");
    } finally {
      setSavingProfile(false);
    }
  };

  const savePassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (savingPassword) return;
    if (password.new_password !== confirmPassword) {
      setPasswordError("Las contraseñas no coinciden.");
      return;
    }
    setPasswordError(null);
    setSavingPassword(true);
    try {
      await changePassword(password);
      setPassword({ current_password: "", new_password: "" });
      setConfirmPassword("");
      toast.show("Contraseña actualizada.");
    } catch (error) {
      const title = error instanceof ApiError && error.status === 401
        ? "La contraseña actual no es correcta."
        : error instanceof ApiError && error.status === 422
          ? "La nueva contraseña debe tener al menos 8 caracteres."
          : "No pudimos cambiar tu contraseña.";
      toast.show(title, "danger");
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
    <PageFrame title="Mi perfil" subtitle="Gestiona tus datos personales y la seguridad de tu cuenta." state={loadingState}>
      {!profile ? null : <div className="user-ficha__layout">
        <Card title="Tu cuenta" className="user-ficha__account">
          <div className="user-ficha__identity">
            <Avatar name={profile.username} className="user-ficha__avatar" />
            <div className="user-ficha__identity-copy">
              <h3>{profile.username}</h3>
              <Badge tone="success">{roleLabels[profile.role]}</Badge>
            </div>
          </div>
          <div className="user-ficha__login">
            <span>Usuario de acceso</span>
            <strong>{profile.username}</strong>
            <p>Tu rol define los permisos dentro de Lumat.</p>
          </div>
        </Card>
        <div className="user-ficha__details">
          <Card title="Datos personales" icon={UserRound} description="Actualiza cómo te identificas y cómo podemos contactarte." className="user-ficha__form-card">
            <form onSubmit={(event) => void saveProfile(event)}>
              <div className="user-ficha__fields">
                <Input label="Nombre" icon={UserRound} helper="Este nombre se mostrará en tu perfil." value={fields.name} onChange={(event) => setDraft({ ...fields, name: event.target.value })} />
                <Input label="Teléfono (opcional)" icon={Phone} type="tel" helper="Incluye el código de país." value={fields.phone} onChange={(event) => setDraft({ ...fields, phone: event.target.value })} />
              </div>
              <footer className="user-ficha__footer">
                <Button type="button" variant="secondary" disabled={savingProfile} onClick={discardProfile}>Descartar cambios</Button>
                <Button type="submit" disabled={savingProfile}><Icon icon={Save} />{savingProfile ? "Guardando…" : "Guardar cambios"}</Button>
              </footer>
            </form>
          </Card>
          <Card title="Seguridad" icon={ShieldCheck} description="Cambia tu contraseña de acceso." className="user-ficha__form-card">
            <form onSubmit={(event) => void savePassword(event)}>
              <Input label="Contraseña actual" type="password" revealable icon={LockKeyhole} autoComplete="current-password" required value={password.current_password} onChange={(event) => setPassword({ ...password, current_password: event.target.value })} />
              <div className="user-ficha__fields">
                <Input label="Nueva contraseña" type="password" revealable icon={LockKeyhole} autoComplete="new-password" minLength={8} required value={password.new_password} onChange={(event) => { setPassword({ ...password, new_password: event.target.value }); setPasswordError(null); }} />
                <Input label="Confirmar nueva contraseña" type="password" revealable icon={LockKeyhole} autoComplete="new-password" minLength={8} required error={passwordError ?? undefined} value={confirmPassword} onChange={(event) => { setConfirmPassword(event.target.value); setPasswordError(null); }} />
              </div>
              <span className="field__helper">Usa una contraseña única y difícil de adivinar.</span>
              <footer className="user-ficha__footer user-ficha__footer--end">
                <Button type="submit" disabled={savingPassword}>{savingPassword ? "Actualizando…" : "Actualizar contraseña"}</Button>
              </footer>
            </form>
          </Card>
        </div>
      </div>}
    </PageFrame>
  );
}
