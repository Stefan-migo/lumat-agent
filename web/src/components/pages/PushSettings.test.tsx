import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PushSettings } from "./PushSettings";

describe("PushSettings", () => {
  it("explains fallback when push is unsupported", () => {
    render(<PushSettings supported={false} />);
    expect(screen.getByText(/notificaciones por correo o whatsapp/i)).toBeInTheDocument();
  });
});
