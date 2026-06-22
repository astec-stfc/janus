import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTheme } from "@/hooks/useTheme";
import { LogOut, Moon, Settings, Sun, User } from "lucide-react";

import gitlabSvg from "@/assets/gitlab.svg";
import { Avatar, AvatarFallback } from "./ui/avatar";

const Navbar = () => {
  const { theme, setTheme: setTheme } = useTheme();

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  return (
    <nav className="bg-sidebar p-4 flex items-center justify-between">
      {/* LEFT */}
      <h1 className="text-xl font-semibold">JANUS</h1>

      {/* RIGHT */}
      <div className="flex items-center gap-4 ">
        {/* THEME TOGGLE */}
        <Button variant="outline" size="icon" onClick={toggleTheme}>
          <Sun className="h-[1.2rem] w-[1.2rem] scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
          <Moon className="absolute h-[1.2rem] w-[1.2rem] scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0" />
          <span className="sr-only">Toggle theme</span>
        </Button>

        {/* GITLAB BUTTON */}
        <Button variant="outline" size="icon" asChild>
          <a
            href="https://gitlab.stfc.ac.uk/janus/janus/"
            target="_blank"
            rel="noopener noreferrer"
          >
            <img src={gitlabSvg} alt="GitLab" className="h-10 w-10" />
            <span className="sr-only">GitLab</span>
          </a>
        </Button>

        {/* USER MENU */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline">
              <Avatar>
                {/* <AvatarImage src="https://some.valid.png.com/example.png" /> */}
                <AvatarFallback>AB</AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent sideOffset={10} align="end">
            <DropdownMenuLabel>@Username</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <User />
              Profile
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings />
              Settings
            </DropdownMenuItem>
            <DropdownMenuItem variant="destructive">
              <LogOut />
              Sign Out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </nav>
  );
};
export default Navbar;
