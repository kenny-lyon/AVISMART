import { createContext, useContext, useEffect, useState } from "react";
import { api, cerrarSesionLocal, guardarSesion, iniciarSoporte, leerToken, terminarSoporte, type Usuario } from "./api";

type AuthState = {
  usuario: Usuario | null;
  listo: boolean;
  entrar: (email: string, password: string) => Promise<Usuario>;
  cambiarClave: (actual: string, nueva: string) => Promise<void>;
  salir: () => void;
  entrarSoporte: (organizacionId: number) => Promise<void>;
  salirSoporte: () => Promise<void>;
  actualizarUsuario: (u: Usuario) => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [listo, setListo] = useState(false);

  useEffect(() => {
    if (!leerToken()) {
      setListo(true);
      return;
    }
    api<Usuario>("/me")
      .then(setUsuario)
      .catch(() => cerrarSesionLocal())
      .finally(() => setListo(true));
  }, []);

  async function entrar(email: string, password: string) {
    const data = await api<{ token: string; usuario: Usuario }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    guardarSesion(data.token);
    setUsuario(data.usuario);
    return data.usuario;
  }

  async function cambiarClave(actual: string, nueva: string) {
    const { token, ...actualizado } = await api<Usuario & { token: string }>("/auth/cambiar-clave", {
      method: "POST",
      body: JSON.stringify({ clave_actual: actual, clave_nueva: nueva }),
    });
    // Cambiar la clave cierra las demás sesiones; esta sigue con el token nuevo.
    guardarSesion(token);
    setUsuario(actualizado);
  }

  function salir() {
    cerrarSesionLocal();
    setUsuario(null);
  }

  async function entrarSoporte(organizacionId: number) {
    const data = await api<{ token: string; usuario: Usuario }>(`/plataforma/organizaciones/${organizacionId}/soporte`, { method: "POST" });
    iniciarSoporte(data.token);
    setUsuario(data.usuario);
  }

  async function salirSoporte() {
    if (!terminarSoporte()) {
      setUsuario(null);
      return;
    }
    try {
      setUsuario(await api<Usuario>("/me"));
    } catch {
      cerrarSesionLocal();
      setUsuario(null);
    }
  }

  return (
    <AuthContext.Provider value={{ usuario, listo, entrar, cambiarClave, salir, entrarSoporte, salirSoporte, actualizarUsuario: setUsuario }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("Auth fuera de contexto");
  return ctx;
}
