import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, updateProject } from "../api/projects";
import { useAuth } from "../context/AuthContext";
import ProjectForm from "../components/ProjectForm";
import { notifySuccess } from "../lib/toast";

export default function EditProject() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [forbidden, setForbidden] = useState(false);

  useEffect(() => {
    getProject(id)
      .then(({ data }) => {
        if (user && data.creator.id !== user.id) {
          setForbidden(true);
        } else {
          setProject(data);
        }
      })
      .finally(() => setLoading(false));
  }, [id, user]);

  const handleSubmit = async (formData) => {
    await updateProject(id, formData);
    notifySuccess("Your project changes have been saved.");
    navigate(`/projects/${id}`);
  };

  if (loading) return <div className="page">Loading...</div>;

  if (forbidden) {
    return (
      <div className="page" style={{ textAlign: "center" }}>
        <h1 className="section-heading">
          You do not have permission to edit this project.
        </h1>
      </div>
    );
  }

  if (!project) return null;

  return (
    <div>
      <div className="container" style={{ paddingTop: 40 }}>
        <h1 className="section-heading">Edit Project</h1>
      </div>

      <ProjectForm
        initial={project}
        existingImages={project.images || []}
        onSubmit={handleSubmit}
        submitLabel="Save Changes"
      />
    </div>
  );
}