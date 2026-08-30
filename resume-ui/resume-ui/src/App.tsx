import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import { Layout } from './components/Layout'
import { Spinner } from './components/ui'
import { Account } from './pages/Account'
import { History } from './pages/History'
import { Home } from './pages/Home'
import { Landing } from './pages/Landing'
import { NotFound } from './pages/NotFound'
import { Report } from './pages/Report'
import { Result } from './pages/Result'
import { ResumeDetail } from './pages/ResumeDetail'
import { Resumes } from './pages/Resumes'
import { SignIn } from './pages/SignIn'
import { SignUp } from './pages/SignUp'
import { HowItWorks, Terms, Privacy } from './pages/static'

function AcademicBanner() {
  return (
    <div className="border-b border-ink-line bg-well px-4 py-1.5 text-center text-[12.5px] font-medium text-mark-critical">
      This app was built for academic purposes.
    </div>
  )
}

function FullPageSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center text-ink-muted">
      <Spinner className="size-6" />
    </div>
  )
}

export default function App() {
  const { user, loading } = useAuth()
  const location = useLocation()
  // The report page prints as a bare document; keep the banner off it.
  const showBanner = !location.pathname.endsWith('/report')

  if (loading) return <FullPageSpinner />

  if (!user) {
    return (
      <>
        {showBanner && <AcademicBanner />}
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/signin" element={<SignIn />} />
          <Route path="/signup" element={<SignUp />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="/terms" element={<Terms />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </>
    )
  }

  return (
    <>
      {showBanner && <AcademicBanner />}
      <Routes>
      {/* The report renders without app chrome so it prints as a document. */}
      <Route path="/analyses/:analysisId/report" element={<Report />} />
      <Route path="/signin" element={<Navigate to="/" replace />} />
      <Route path="/signup" element={<Navigate to="/" replace />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/resumes" element={<Resumes />} />
        <Route path="/resumes/:resumeId" element={<ResumeDetail />} />
        <Route path="/analyses/:analysisId" element={<Result />} />
        <Route path="/history" element={<History />} />
        <Route path="/account" element={<Account />} />
        <Route path="/how-it-works" element={<HowItWorks />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="*" element={<NotFound />} />
      </Route>
      </Routes>
    </>
  )
}
