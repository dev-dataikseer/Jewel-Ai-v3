import { StudioProvider } from "./studio/StudioContext";
import { StudioLayout } from "./studio/StudioLayout";

export function StudioPage() {
  return (
    <StudioProvider>
      <StudioLayout />
    </StudioProvider>
  );
}
