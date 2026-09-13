import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import RequireAuth from "./components/RequireAuth";

import Home from "./pages/Home";
import Register from "./pages/Register";
import Login from "./pages/Login";
import Activation from "./pages/Activation";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import Profile from "./pages/Profile";
import MyProjects from "./pages/MyProjects";
import MyDonations from "./pages/MyDonations";
import CreateProject from "./pages/CreateProject";
import EditProject from "./pages/EditProject";
import ProjectList from "./pages/ProjectList";
import ProjectDetail from "./pages/ProjectDetail";
import CategoryProjects from "./pages/CategoryProjects";
import SearchResults from "./pages/SearchResults";

// Route map straight from PROJECT_SPEC.md section 14.
// Guarded routes match the "requires authentication" list there exactly.
export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/register" element={<Register />} />
        <Route path="/login" element={<Login />} />
        <Route path="/activate/:uid/:token" element={<Activation />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password/:uid/:token" element={<ResetPassword />} />
        <Route path="/projects" element={<ProjectList />} />
        <Route path="/projects/:id" element={<ProjectDetail />} />
        <Route path="/categories/:slug" element={<CategoryProjects />} />
        <Route path="/search" element={<SearchResults />} />

        <Route
          path="/profile"
          element={
            <RequireAuth>
              <Profile />
            </RequireAuth>
          }
        />
        <Route
          path="/my-projects"
          element={
            <RequireAuth>
              <MyProjects />
            </RequireAuth>
          }
        />
        <Route
          path="/my-donations"
          element={
            <RequireAuth>
              <MyDonations />
            </RequireAuth>
          }
        />
        <Route
          path="/projects/new"
          element={
            <RequireAuth>
              <CreateProject />
            </RequireAuth>
          }
        />
        <Route
          path="/projects/:id/edit"
          element={
            <RequireAuth>
              <EditProject />
            </RequireAuth>
          }
        />
      </Routes>
    </Layout>
  );
}
