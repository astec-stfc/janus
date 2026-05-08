import AppSidebar from "@/components/AppSidebar";
import Navbar from "@/components/Navbar";
import { SidebarProvider } from "@/components/ui/sidebar";
import { PVWSProvider } from "@/providers/PVWSProvider";
import { ThemeProvider } from "@/providers/ThemeProvider";
import { appRoutes } from "@/routes";
import { Route, Routes } from "react-router-dom";

function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
      <PVWSProvider>
        <SidebarProvider>
          <div className="flex h-screen w-full flex-col overflow-hidden">
            <Navbar />
            <div className="flex min-h-0 w-full flex-1 bg-sidebar">
              <AppSidebar />
              <main className="mr-2 mb-2 flex-1 overflow-hidden rounded-2xl bg-background">
                <Routes>
                  {appRoutes.map((route) => (
                    <Route
                      key={route.path}
                      path={route.path}
                      element={<route.component />}
                    />
                  ))}
                </Routes>
              </main>
            </div>
          </div>
        </SidebarProvider>
      </PVWSProvider>
    </ThemeProvider>
  );
}

export default App;
