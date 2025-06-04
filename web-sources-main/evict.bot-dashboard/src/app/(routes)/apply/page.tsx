"use client"

import { Dialog, Transition } from "@headlessui/react"
import {
    Bug,
    Check,
    ChevronLeft,
    ChevronRight,
    Globe2,
    LineChart,
    Loader2,
    MessagesSquare,
    Shield,
    Sparkles,
    Workflow,
    X
} from "lucide-react"
import { useSession } from "next-auth/react"
import { useRouter } from "next/navigation"
import { Fragment, useMemo, useState } from "react"
import { toast } from "react-hot-toast"

type Role = {
    id: string
    title: string
    description: string
    icon: any
    status: "available" | "coming_soon"
    color: string
    requirements: string[]
    timeCommitment: string
    benefits: string[]
}

type FilterCategory = "Featured" | "Community" | "Technical" | "Strategic" | "All"

type RolePreview = {
    id: string
    title: string
    description: string
    icon: any
    status: "available" | "coming_soon"
    category: string
    benefits: string[]
    requirements: string[]
    timeCommitment: string
}

const roles: RolePreview[] = [
    {
        id: "community-helper",
        title: "Community Helper",
        description: "The first point of contact for user support and guidance",
        icon: MessagesSquare,
        status: "available",
        category: "Community Leadership",
        benefits: [
            "Early access to features",
            "Exclusive helper badge",
            "Direct access to dev team"
        ],
        requirements: [
            "Active community member for 1+ month",
            "Strong communication skills",
            "Basic bot knowledge"
        ],
        timeCommitment: "5-10 hours/week"
    },
    {
        id: "support-staff",
        title: "Support Staff",
        description: "Provide advanced technical support and mentor helpers",
        icon: Shield,
        status: "available",
        category: "Community Leadership",
        benefits: ["Premium bot features", "Staff badge", "Monthly team meetings"],
        requirements: [
            "Previous helper experience",
            "Deep bot knowledge",
            "Problem-solving skills"
        ],
        timeCommitment: "10-15 hours/week"
    },
    {
        id: "beta-tester",
        title: "Beta Tester",
        description: "Test new features before they go live",
        icon: Sparkles,
        status: "available",
        category: "Technical",
        benefits: ["Early feature access", "Beta tester badge", "Direct feedback channel"],
        requirements: [
            "Active Discord user",
            "Attention to detail",
            "Willingness to provide feedback"
        ],
        timeCommitment: "2-5 hours/week"
    },
    {
        id: "qa-engineer",
        title: "QA Engineer",
        description: "Ensure feature quality and reliability",
        icon: Bug,
        status: "coming_soon",
        category: "Technical",
        benefits: ["QA tools access", "Engineer badge", "Team planning access"],
        requirements: ["Testing experience", "Technical background", "Documentation skills"],
        timeCommitment: "8-12 hours/week"
    },
    {
        id: "data-analyst",
        title: "Data Analyst",
        description: "Analyze usage patterns and provide insights",
        icon: LineChart,
        status: "coming_soon",
        category: "Strategic",
        benefits: ["Analytics dashboard access", "Analyst badge", "Strategic planning involvement"],
        requirements: ["Data analysis experience", "SQL knowledge", "Visualization skills"],
        timeCommitment: "10-15 hours/week"
    },
    {
        id: "product-manager",
        title: "Product Manager",
        description: "Plan and prioritize future developments",
        icon: LineChart,
        status: "available",
        category: "Strategic",
        benefits: [
            "Product roadmap access",
            "Product manager badge",
            "Strategic planning involvement"
        ],
        requirements: [
            "Product management experience",
            "Strong analytical skills",
            "Community understanding"
        ],
        timeCommitment: "10-15 hours/week"
    },
    {
        id: "feature-strategist",
        title: "Feature Strategist",
        description: "Plan and prioritize future developments",
        icon: Workflow,
        status: "coming_soon",
        category: "Strategic",
        benefits: ["Roadmap influence", "Strategist badge", "Leadership meetings"],
        requirements: [
            "Product strategy experience",
            "Strong analytical skills",
            "Community understanding"
        ],
        timeCommitment: "8-12 hours/week"
    },
    {
        id: "translator",
        title: "Translator",
        description: "Help make Evict accessible to users worldwide",
        icon: Globe2,
        status: "available",
        category: "Community",
        benefits: [
            "Early access to features",
            "Translator badge",
            "Recognition in translated content",
            "Direct communication with dev team"
        ],
        requirements: [
            "Fluent in English",
            "Native/fluent in target language",
            "Strong attention to detail",
            "Understanding of technical terms"
        ],
        timeCommitment: "3-8 hours/week"
    }
]

export default function ApplicationHub() {
    const router = useRouter()
    const { data: session, status } = useSession()
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [isSuccess, setIsSuccess] = useState(false)
    const [message, setMessage] = useState("")
    const [selectedRole, setSelectedRole] = useState<string | null>(null)
    const [activeCategory, setActiveCategory] = useState<string | null>(null)
    const [isModalOpen, setIsModalOpen] = useState(false)
    const [activeFilter, setActiveFilter] = useState<FilterCategory>("Featured")

    const filterButtons: FilterCategory[] = [
        "Featured",
        "Community",
        "Technical",
        "Strategic",
        "All"
    ]

    const filteredRoles = useMemo(() => {
        if (activeFilter === "All") return roles
        if (activeFilter === "Featured") {
            return roles.filter(role => role.status === "available")
        }
        return roles.filter(role =>
            role.category.toLowerCase().includes(activeFilter.toLowerCase())
        )
    }, [activeFilter])

    const selectedRoleData = useMemo(
        () => roles.find(role => role.id === selectedRole),
        [selectedRole]
    )

    if (status === "loading") {
        return (
            <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="w-8 h-8 text-white/60 animate-spin mx-auto mb-4" />
                    <p className="text-white/60">Loading...</p>
                </div>
            </div>
        )
    }

    if (status === "unauthenticated") {
        router.push("/login?forBeta=true")
        return null
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setIsSubmitting(true)

        try {
            const response = await fetch("/api/beta", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    role_id: selectedRole,
                    display_name: session?.user?.name,
                    description: message,
                    discord_id: session?.user?.id,
                    email: session?.user?.email,
                    role_info: {
                        title: selectedRoleData?.title,
                        category: selectedRoleData?.category,
                        time_commitment: selectedRoleData?.timeCommitment
                    },
                    application_metadata: {
                        submitted_at: new Date().toISOString(),
                        platform: "website",
                        status: "pending"
                    }
                })
            })

            if (!response.ok) {
                const error = await response.json()
                toast.error(error.message || "Failed to submit application")
                return
            }

            toast.success("Application submitted successfully")
            setIsSuccess(true)
        } catch (error) {
            toast.error("Failed to submit application")
            console.error("Application submission error:", error)
        } finally {
            setIsSubmitting(false)
        }
    }

    const openApplicationModal = (role: Role) => {
        setSelectedRole(role.id)
        setIsModalOpen(true)
    }

    const closeApplicationModal = () => {
        setIsModalOpen(false)
        setSelectedRole(null)
    }

    if (isSuccess) {
        return (
            <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
                <div className="text-center">
                    <div className="bg-green-500/10 p-4 rounded-full inline-block mb-4">
                        <Check className="w-8 h-8 text-green-500" />
                    </div>
                    <h1 className="text-2xl font-bold text-white mb-2">Application Submitted!</h1>
                    <p className="text-white/60 max-w-md mx-auto">
                        Thank you for your interest in joining our team. We&apos;sll review your
                        application and get back to you soon.
                    </p>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-[#0A0A0B]">
            <div className="relative bg-gradient-to-b from-[#1A1B1E] to-[#0A0A0B]">
                <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.02]" />
                <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-[3.5rem]">
                    <div className="max-w-3xl">
                        <h1 className="text-5xl font-bold text-white mb-6 leading-tight">
                            Turn your passion for
                            <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
                                {" "}
                                community building{" "}
                            </span>
                            into impact.
                        </h1>
                        <p className="text-xl text-gray-400 leading-relaxed">
                            Join Evict&apos;s team of innovators and help create the next generation
                            of Discord moderation tools. Whether you&apos;re a community expert or a
                            tech enthusiast, there&apos;s a place for you here.
                        </p>
                    </div>
                </div>
            </div>

            <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
                <div className="bg-gradient-to-r from-indigo-500/10 to-purple-500/10 rounded-2xl border border-indigo-500/20 p-8 relative overflow-hidden">
                    <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.02]" />
                    <div className="relative flex flex-col md:flex-row items-center justify-between gap-8">
                        <div className="flex-1">
                            <div className="flex items-center gap-2 mb-4">
                                <Sparkles className="w-5 h-5 text-indigo-400" />
                                <span className="text-indigo-400 font-medium">
                                    Featured Opportunity
                                </span>
                            </div>
                            <h2 className="text-3xl font-bold text-white mb-4">
                                Become a Beta Tester
                            </h2>
                            <p className="text-lg text-gray-300 mb-6">
                                Get early access to new features, provide valuable feedback, and
                                help shape the future of Evict. We&apos;re looking for enthusiastic
                                community members to join our beta testing program.
                            </p>
                            <ul className="space-y-3 mb-8">
                                <li className="flex items-center gap-2 text-gray-300">
                                    <Check className="w-5 h-5 text-emerald-500" />
                                    Only 2-5 hours per week required
                                </li>
                                <li className="flex items-center gap-2 text-gray-300">
                                    <Check className="w-5 h-5 text-emerald-500" />
                                    Early access to upcoming features
                                </li>
                                <li className="flex items-center gap-2 text-gray-300">
                                    <Check className="w-5 h-5 text-emerald-500" />
                                    Direct communication with the dev team
                                </li>
                            </ul>
                            <button
                                onClick={() => setSelectedRole("beta-tester")}
                                className="px-6 py-3 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg font-medium transition-all duration-200 inline-flex items-center gap-2">
                                Apply for Beta Testing
                                <ChevronRight className="w-4 h-4" />
                            </button>
                        </div>
                        <div className="flex-shrink-0">
                            <div className="w-48 h-48 rounded-full bg-indigo-500/20 flex items-center justify-center">
                                <Sparkles className="w-24 h-24 text-indigo-400" />
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16  border-white/10">
                <div className="flex flex-col md:flex-row items-center justify-between gap-8">
                    <div className="flex-1">
                        <h2 className="text-3xl font-bold text-white mb-4">Meet Our Team</h2>
                        <p className="text-lg text-gray-300 mb-6">
                            Join a passionate group of community builders, developers, and
                            innovators who are shaping the future of Discord moderation. Get to know
                            the faces behind Evict and see where you might fit in.
                        </p>
                        <button
                            onClick={() => router.push("/team")}
                            className="px-6 py-3 bg-white/5 hover:bg-white/10 text-white rounded-lg font-medium transition-all duration-200 inline-flex items-center gap-2 border border-white/10">
                            Meet the Team
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                    <div className="flex-shrink-0">
                        <div className="w-64 h-64 rounded-2xl bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border border-indigo-500/20 flex items-center justify-center">
                            <div className="grid grid-cols-2 gap-2 p-4">
                                <div className="w-12 h-12 rounded-full bg-white/10"></div>
                                <div className="w-12 h-12 rounded-full bg-white/10"></div>
                                <div className="w-12 h-12 rounded-full bg-white/10"></div>
                                <div className="w-12 h-12 rounded-full bg-white/[0.15]"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                {!selectedRole ? (
                    <>
                        <div className="mb-12">
                            <h2 className="text-2xl font-semibold text-white mb-6">Filters</h2>
                            <div className="flex flex-wrap gap-3">
                                {filterButtons.map(filter => (
                                    <button
                                        key={filter}
                                        onClick={() => setActiveFilter(filter)}
                                        className={`
                                            px-6 py-2 rounded-full text-sm font-medium transition-all
                                            ${
                                                activeFilter === filter
                                                    ? "bg-indigo-500 text-white"
                                                    : "bg-white/5 text-white/70 hover:bg-white/10"
                                            }
                                        `}>
                                        {filter}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {filteredRoles.map(role => (
                                <button
                                    key={role.id}
                                    onClick={() =>
                                        role.status === "available" && setSelectedRole(role.id)
                                    }
                                    className={`
                                        text-left relative overflow-hidden rounded-xl border border-white/10
                                        ${role.status === "available" ? "cursor-pointer" : "opacity-75"}
                                        bg-white/[0.02] backdrop-blur-sm group hover:bg-white/[0.04] transition-all
                                        p-6
                                    `}>
                                    <role.icon className="w-8 h-8 text-white/80 mb-4" />

                                    <h3 className="text-xl font-semibold text-white mb-2">
                                        {role.title}
                                    </h3>

                                    <p className="text-white/60 mb-4">{role.description}</p>

                                    {role.status === "coming_soon" ? (
                                        <span className="inline-block px-3 py-1 rounded-full text-sm font-medium bg-white/10 text-white/60">
                                            Coming Soon
                                        </span>
                                    ) : (
                                        <span className="inline-flex items-center text-sm font-medium text-indigo-400">
                                            Learn More
                                            <ChevronRight className="w-4 h-4 ml-1" />
                                        </span>
                                    )}
                                </button>
                            ))}
                        </div>
                    </>
                ) : (
                    <div className="max-w-7xl mx-auto space-y-12">
                        <button
                            onClick={() => setSelectedRole(null)}
                            className="flex items-center text-zinc-400 hover:text-white transition-colors">
                            <ChevronLeft className="w-5 h-5 mr-2" />
                            Back to all positions
                        </button>

                        <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4">
                            <div className="flex items-start">
                                <div className="flex-shrink-0">
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        className="h-5 w-5 text-amber-400 mt-0.5"
                                        viewBox="0 0 20 20"
                                        fill="currentColor">
                                        <path
                                            fillRule="evenodd"
                                            d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                                            clipRule="evenodd"
                                        />
                                    </svg>
                                </div>
                                <div className="ml-3">
                                    <h3 className="text-sm font-medium text-amber-400">
                                        Important Notice
                                    </h3>
                                    <div className="mt-1 text-sm text-amber-300/80">
                                        Please review your application carefully before submitting.
                                        You can only apply once for each role, and applications
                                        cannot be modified after submission. Make sure to provide
                                        detailed and thoughtful responses that accurately represent
                                        your qualifications and enthusiasm for the position.
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="flex items-start justify-between">
                            {(() => {
                                const Icon = selectedRoleData?.icon
                                return (
                                    <>
                                        <div>
                                            <h1 className="text-4xl font-bold text-white mb-3">
                                                {selectedRoleData?.title}
                                            </h1>
                                            <p className="text-lg text-zinc-400">
                                                {selectedRoleData?.description}
                                            </p>
                                        </div>
                                        <Icon className="w-12 h-12 text-zinc-300" />
                                    </>
                                )
                            })()}
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                            <div>
                                <h2 className="text-xl font-semibold text-white mb-6">
                                    Requirements
                                </h2>
                                <ul className="space-y-4">
                                    {selectedRoleData?.requirements.map((req, i) => (
                                        <li key={i} className="flex items-start text-zinc-400">
                                            <Check className="w-5 h-5 text-emerald-500 mt-0.5 mr-3 flex-shrink-0" />
                                            <span>{req}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            <div>
                                <h2 className="text-xl font-semibold text-white mb-6">Benefits</h2>
                                <ul className="space-y-4">
                                    {selectedRoleData?.benefits.map((benefit, i) => (
                                        <li key={i} className="flex items-start text-zinc-400">
                                            <Sparkles className="w-5 h-5 text-amber-400 mt-0.5 mr-3 flex-shrink-0" />
                                            <span>{benefit}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        <div>
                            <h2 className="text-xl font-semibold text-white mb-4">
                                Time Commitment
                            </h2>
                            <p className="text-zinc-400">{selectedRoleData?.timeCommitment}</p>
                        </div>

                        <div className="flex justify-center pt-6">
                            <button
                                onClick={() => setIsModalOpen(true)}
                                className="px-8 py-3 bg-zinc-100 hover:bg-white text-zinc-900 
                                         rounded-lg font-medium transition-colors duration-200 
                                         shadow-lg hover:shadow-xl">
                                Apply Now
                            </button>
                        </div>
                    </div>
                )}
            </div>

            <Transition appear show={isModalOpen} as={Fragment}>
                <Dialog as="div" className="relative z-50" onClose={closeApplicationModal}>
                    <Transition.Child
                        as={Fragment}
                        enter="ease-out duration-300"
                        enterFrom="opacity-0"
                        enterTo="opacity-100"
                        leave="ease-in duration-200"
                        leaveFrom="opacity-100"
                        leaveTo="opacity-0">
                        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm" />
                    </Transition.Child>

                    <div className="fixed inset-0 overflow-y-auto">
                        <div className="flex min-h-full items-center justify-center p-4">
                            <Transition.Child
                                as={Fragment}
                                enter="ease-out duration-300"
                                enterFrom="opacity-0 scale-95"
                                enterTo="opacity-100 scale-100"
                                leave="ease-in duration-200"
                                leaveFrom="opacity-100 scale-100"
                                leaveTo="opacity-0 scale-95">
                                <Dialog.Panel className="w-full max-w-2xl transform overflow-hidden rounded-2xl bg-[#1A1A1B] border border-white/10 p-6 shadow-xl transition-all">
                                    <div className="flex justify-between items-start mb-6">
                                        <Dialog.Title className="text-2xl font-semibold text-white">
                                            Apply for {selectedRoleData?.title}
                                        </Dialog.Title>
                                        <button
                                            onClick={closeApplicationModal}
                                            className="text-white/60 hover:text-white">
                                            <X className="w-6 h-6" />
                                        </button>
                                    </div>

                                    <div className="mb-6 bg-amber-500/10 border border-amber-500/20 rounded-lg p-4">
                                        <div className="flex items-start">
                                            <div className="flex-shrink-0">
                                                <svg
                                                    xmlns="http://www.w3.org/2000/svg"
                                                    className="h-5 w-5 text-amber-400 mt-0.5"
                                                    viewBox="0 0 20 20"
                                                    fill="currentColor">
                                                    <path
                                                        fillRule="evenodd"
                                                        d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                                                        clipRule="evenodd"
                                                    />
                                                </svg>
                                            </div>
                                            <div className="ml-3">
                                                <h3 className="text-sm font-medium text-amber-400">
                                                    Important Notice
                                                </h3>
                                                <div className="mt-1 text-sm text-amber-300/80">
                                                    Please review your application carefully before
                                                    submitting. You can only apply once for each
                                                    role, and applications cannot be modified after
                                                    submission. Make sure to provide detailed and
                                                    thoughtful responses that accurately represent
                                                    your qualifications and enthusiasm for the
                                                    position.
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    <form onSubmit={handleSubmit} className="space-y-6">
                                        <div>
                                            <label className="block text-sm font-medium text-white/60 mb-2">
                                                Discord ID
                                            </label>
                                            <input
                                                type="text"
                                                disabled
                                                value={session?.user?.id || ""}
                                                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white disabled:opacity-50 font-mono"
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium text-white/60 mb-2">
                                                Name
                                            </label>
                                            <input
                                                type="text"
                                                disabled
                                                value={session?.user?.name || ""}
                                                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white disabled:opacity-50"
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium text-white/60 mb-2">
                                                Email
                                            </label>
                                            <input
                                                type="email"
                                                disabled
                                                value={session?.user?.email || ""}
                                                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white disabled:opacity-50"
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium text-white/60 mb-2">
                                                Why do you want to join our team?
                                            </label>
                                            <textarea
                                                value={message}
                                                onChange={e => setMessage(e.target.value)}
                                                required
                                                rows={4}
                                                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white resize-none focus:outline-none focus:ring-2 focus:ring-white/20"
                                                placeholder="Tell us about your motivation and qualifications..."
                                            />
                                        </div>

                                        <button
                                            type="submit"
                                            disabled={isSubmitting || !message}
                                            className="px-12 py-3 bg-zinc-100 hover:bg-white text-zinc-900 
                                                     rounded-lg font-medium transition-all duration-200 
                                                     disabled:opacity-50 disabled:cursor-not-allowed 
                                                     flex items-center justify-center">
                                            {isSubmitting ? (
                                                <>
                                                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                                                    Submitting...
                                                </>
                                            ) : (
                                                "Submit Application"
                                            )}
                                        </button>
                                    </form>
                                </Dialog.Panel>
                            </Transition.Child>
                        </div>
                    </div>
                </Dialog>
            </Transition>
        </div>
    )
}
