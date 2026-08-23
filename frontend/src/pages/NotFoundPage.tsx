/**
 * 404 page for unknown routes.
 */

import { useNavigate } from "react-router-dom"
import { HelpCircle } from "lucide-react"

export default function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="empty-state">
      <HelpCircle size={36} />
      <strong>Page not found</strong>
      <p>The requested page does not exist in the research terminal.</p>
      <button className="refresh-button" onClick={() => navigate("/")}>
        Return to Research Home
      </button>
    </div>
  )
}
