import HeroSection from './components/HeroSection';
import Navbar from './components/Navbar';
import { createBrowserRouter, RouterProvider } from "react-router";
import { Outlet } from "react-router";

function Layout() {
  return (
    <div>
      <Navbar />
      <Outlet />
    </div>
  );
}

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      {path: "", element: <HeroSection />},
      // {path: "results", element: <Navbar />},
    ]
  },
]);

function App() {
  return (
    <>
      <RouterProvider router={router} />
    </>
  )
}

export default App;
