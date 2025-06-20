"use client"
import { Category } from "@/types/Command"
import { ReactNode, useEffect, useRef, useState } from "react"

export const CategorySelector = ({
    categories,
    selected,
    onClick
}: {
    categories: Category[]
    selected: string
    onClick: (category: string) => void
}) => {
    const scrollContainerRef = useRef<HTMLDivElement>(null)
    const [isScrolling, setIsScrolling] = useState(false)
    const [scrollPosition, setScrollPosition] = useState<number>(0)
    const [showLeftArrow, setShowLeftArrow] = useState(false)
    const [showRightArrow, setShowRightArrow] = useState(false)

    const scroll = (direction: "left" | "right") => {
        const scrollAmount = 350
        const list = scrollContainerRef.current

        if (list) {
            const maxScrollLeft = list.scrollWidth - list.clientWidth
            const newPosition =
                direction === "left"
                    ? Math.max(0, scrollPosition - scrollAmount)
                    : Math.min(maxScrollLeft, scrollPosition + scrollAmount)

            setScrollPosition(newPosition)

            list.scrollTo({
                left: newPosition,
                behavior: "smooth"
            })
        }
    }

    const handleCategoryClick = (category: string) => {
        if (!isScrolling) {
            onClick(category)
            scrollToCategory(category)
        }
    }

    const scrollToCategory = (category: string) => {
        const container = scrollContainerRef.current
        const categoryElement = container?.querySelector(
            `[data-category="${category}"]`
        ) as HTMLElement

        if (container && categoryElement) {
            const scrollLeft =
                categoryElement.offsetLeft -
                container.offsetWidth / 2 +
                categoryElement.offsetWidth / 2
            container.scrollTo({ left: scrollLeft, behavior: "smooth" })
            setScrollPosition(scrollLeft)
        }
    }

    useEffect(() => {
        const container = scrollContainerRef.current
        if (container) {
            const handleScroll = () => {
                setScrollPosition(container.scrollLeft)
                setShowLeftArrow(container.scrollLeft > 0)
                setShowRightArrow(
                    Math.ceil(container.scrollLeft + container.clientWidth) < container.scrollWidth
                )
            }

            // Initial check
            handleScroll()

            // Add scroll listener
            container.addEventListener("scroll", handleScroll)
            return () => container.removeEventListener("scroll", handleScroll)
        }
    }, [])

    return (
        <div className="relative">
            <button
                className={`absolute pl-4 left-0 z-50 inset-y-0 backdrop-blur-[1px] bg-[#110f112f] flex items-center text-neutral-300 transition duration-200 ease-linear hover:text-white ${
                    showLeftArrow ? "flex" : "hidden"
                }`}
                onClick={() => scroll("left")}>
                <svg
                    width="1.5em"
                    height="1.5em"
                    viewBox="0 0 24 24"
                    strokeWidth="2"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                    color="currentColor"
                    className="h-6 w-6 inline-block">
                    <path
                        d="M21 12L3 12M3 12L11.5 3.5M3 12L11.5 20.5"
                        stroke="currentColor"
                        strokeLinecap="round"
                        strokeLinejoin="round"></path>
                </svg>
            </button>
            <div
                ref={scrollContainerRef}
                className="mt-10 flex items-center overflow-x-auto no-scrollbar h-[60px] bg-marly-200 rounded-2xl w-full border border-marly-card-border"
                onMouseDown={event => {
                    let startX = event.pageX
                    let scrollLeft = scrollContainerRef.current?.scrollLeft || 0

                    const handleMouseMove = (event: MouseEvent) => {
                        const distance = event.pageX - startX
                        scrollContainerRef.current!.scrollLeft = scrollLeft - distance
                        setScrollPosition(scrollContainerRef.current!.scrollLeft)
                        setIsScrolling(true)
                    }

                    const handleMouseUp = () => {
                        if (!isScrolling) {
                            scrollContainerRef.current!.style.pointerEvents = "auto"
                        }
                        document.removeEventListener("mousemove", handleMouseMove)
                        document.removeEventListener("mouseup", handleMouseUp)
                    }

                    document.addEventListener("mousemove", handleMouseMove)
                    document.addEventListener("mouseup", handleMouseUp)

                    setTimeout(() => {
                        if (!isScrolling) {
                            scrollContainerRef.current!.style.pointerEvents = "auto"
                        }
                        setIsScrolling(false)
                    }, 20)
                }}
                onClick={event => {
                    if (isScrolling) {
                        event.preventDefault()
                        event.stopPropagation()
                    }
                }}>
                {categories.map((category: Category) => (
                    <SelectorItem
                        key={category.name}
                        name={category.name}
                        amount={category.commands.length.toString()}
                        icon={category.icon}
                        scrolling={isScrolling}
                        active={selected}
                        setCategory={handleCategoryClick}
                    />
                ))}
            </div>
            <button
                className={`absolute px-4 right-0 z-50 inset-y-0 backdrop-blur-[1px] bg-[#110f112f] flex items-center text-neutral-300 transition duration-200 ease-linear hover:text-white ${
                    showRightArrow ? "flex" : "hidden"
                }`}
                onClick={() => scroll("right")}>
                <svg
                    width="1.5em"
                    height="1.5em"
                    viewBox="0 0 24 24"
                    strokeWidth="2"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                    color="currentColor"
                    className="h-6 w-6 inline-block">
                    <path
                        d="M3 12L21 12M21 12L12.5 3.5M21 12L12.5 20.5"
                        stroke="currentColor"
                        strokeLinecap="round"
                        strokeLinejoin="round"></path>
                </svg>
            </button>
        </div>
    )
}

const SelectorItem = ({
    name,
    amount,
    icon,
    scrolling,
    active,
    setCategory
}: {
    name: string
    amount: string
    icon: ReactNode
    scrolling: boolean
    active: string
    setCategory: (category: string) => void
}) => {
    return (
        <button
            data-category={name}
            className={`flex flex-row gap-2 items-center h-full px-7 ${active == name ? "text-white bg-marly-300" : "text-marly-700 bg-marly-900 hover:bg-marly-dim hover:text-white"}`}
            onClick={() => !scrolling && setCategory(name)}>
            <div className="text-marly-main font-bold text-lg">{icon}</div>
            <span
                className={`font-bold ${active != name ? "text-marly-unselected" : ""} text-base`}>
                {name}
            </span>
            <div
                className={`flex font-bold ${active != name ? "bg-marly-500" : "bg-marly-700"} px-2 py-1 rounded-lg`}>
                <span
                    className={`text-sm font-semibold ${active != name ? "text-marly-unselected" : "text-white"}`}>
                    {amount}
                </span>
            </div>
        </button>
    )
}
